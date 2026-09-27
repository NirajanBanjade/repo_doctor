"""Parse the user-supplied feature wiki into an authoritative architecture map."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

from app.analysis.base_adapter import GraphEdge, GraphNode

_TITLE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_SECTION = re.compile(r"^##\s+(Frontend|Backend)\s*$", re.MULTILINE | re.IGNORECASE)
_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[[^]]+\]\(([^)]+\.md)\)")
_FILE_TOKEN = re.compile(r"(?:^|/)[\w.-]+\.[A-Za-z0-9]+$")


@dataclass
class WikiFeature:
    feature_id: str
    name: str
    description: str
    document: str
    frontend_files: list[str] = field(default_factory=list)
    backend_files: list[str] = field(default_factory=list)
    file_edges: list[tuple[str, str]] = field(default_factory=list)
    connected_feature_ids: list[str] = field(default_factory=list)

    @property
    def files(self) -> list[str]:
        return list(dict.fromkeys(self.frontend_files + self.backend_files))


@dataclass
class WikiArchitecture:
    features: list[WikiFeature]
    warnings: list[str]


def parse_feature_wiki(repo_path: str, wiki_path: str) -> WikiArchitecture:
    """Parse one feature per Markdown page; README is an index, not a feature."""
    root = Path(repo_path).resolve()
    wiki = Path(wiki_path).resolve()
    features: list[WikiFeature] = []
    warnings: list[str] = []

    for page in sorted(wiki.glob("*.md")):
        if page.name.lower() == "readme.md":
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        title = _TITLE.search(text)
        if not title:
            warnings.append(f"{page.name}: missing level-one feature title")
            continue
        sections = _section_bodies(text)
        frontend = _extract_files(
            sections.get("frontend", ""), root, _section_root(root, "frontend")
        )
        backend = _extract_files(
            sections.get("backend", ""), root, _section_root(root, "backend")
        )
        files = list(dict.fromkeys(frontend + backend))
        for path in files:
            if not (root / path).is_file():
                warnings.append(f"{page.name}: documented file not found: {path}")
        links = [Path(target).stem for target in _LINK.findall(text)]
        features.append(
            WikiFeature(
                feature_id=page.stem,
                name=title.group(1).strip(),
                description=_description(text, title.end()),
                document=str(page.relative_to(wiki)),
                frontend_files=frontend,
                backend_files=backend,
                file_edges=_extract_flow_edges(sections, root),
                connected_feature_ids=list(dict.fromkeys(links)),
            )
        )
    return WikiArchitecture(features=features, warnings=warnings)


def build_wiki_graph(
    architecture: WikiArchitecture,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Create the file-level graph used by X-Ray, ImpactScope, and test planning."""
    owners = {path: f.feature_id for f in architecture.features for path in f.files}
    nodes = [
        GraphNode(
            node_id=f"file:{path}",
            kind="file",
            name=Path(path).name,
            path=path,
            line_start=1,
            line_end=1,
            language=Path(path).suffix.lstrip(".") or "unknown",
            summary=f"Owned by feature: {feature.name}",
        )
        for feature in architecture.features
        for path in feature.files
    ]
    unique_nodes = {node.node_id: node for node in nodes}
    edges: list[GraphEdge] = []
    seen: set[tuple[str, str]] = set()
    for feature in architecture.features:
        for source, target in feature.file_edges:
            key = (source, target)
            if key in seen or source not in owners or target not in owners:
                continue
            seen.add(key)
            edges.append(
                GraphEdge(
                    source_id=f"file:{source}",
                    target_id=f"file:{target}",
                    relationship="uses",
                    file=feature.document,
                    line=1,
                    evidence_status="confirmed_static",
                    note="Documented by the authoritative feature wiki",
                )
            )
        if feature.frontend_files and feature.backend_files:
            boundary = (feature.frontend_files[-1], feature.backend_files[0])
            if boundary not in seen:
                seen.add(boundary)
                edges.append(
                    GraphEdge(
                        source_id=f"file:{boundary[0]}",
                        target_id=f"file:{boundary[1]}",
                        relationship="uses",
                        file=feature.document,
                        line=1,
                        evidence_status="inferred",
                        note=(
                            "Inferred frontend-to-backend boundary from the two "
                            "documented sections; no direct call was statically confirmed"
                        ),
                    )
                )
    return list(unique_nodes.values()), edges


def serialize_architecture(architecture: WikiArchitecture) -> list[dict]:
    return [
        {
            "feature_id": f.feature_id,
            "name": f.name,
            "description": f.description,
            "document": f.document,
            "frontend_files": f.frontend_files,
            "backend_files": f.backend_files,
            "files": f.files,
            "file_edges": [
                {"source": source, "target": target} for source, target in f.file_edges
            ],
            "connected_feature_ids": f.connected_feature_ids,
        }
        for f in architecture.features
    ]


def _section_bodies(text: str) -> dict[str, str]:
    matches = list(_SECTION.finditer(text))
    return {
        match.group(1).lower(): (
            text[match.end() : matches[index + 1].start()]
            if index + 1 < len(matches)
            else text[match.end() :]
        )
        for index, match in enumerate(matches)
    }


def _description(text: str, title_end: int) -> str:
    remainder = text[title_end:]
    section = _SECTION.search(remainder)
    body = remainder[: section.start() if section else len(remainder)]
    return " ".join(line.strip() for line in body.splitlines() if line.strip())


def _section_root(repo: Path, section: str) -> Path:
    """Return the conventional source root for a wiki section."""
    candidates = (
        (Path("frontend/src"), Path("frontend"))
        if section == "frontend"
        else (Path("backend"),)
    )
    return next((path for path in candidates if (repo / path).is_dir()), Path())


def _extract_files(text: str, repo: Path, section_root: Path = Path()) -> list[str]:
    resolved: list[str] = []
    last_dir = Path()
    for token in _CODE.findall(text):
        candidate = token.strip().rstrip(".,;:")
        if (
            candidate.startswith("/")
            or "*" in candidate
            or not _FILE_TOKEN.search(candidate)
        ):
            continue
        path = Path(candidate)
        section_relative = section_root / path
        if len(path.parts) == 1 and last_dir.parts:
            relative = last_dir / path
        else:
            relative = section_relative
        # Explicit repo-relative paths take precedence over section conventions.
        if (repo / path).is_file():
            relative = path
        elif (repo / section_relative).is_file():
            relative = section_relative
        if len(relative.parts) > 1:
            last_dir = relative.parent
        value = relative.as_posix()
        if value not in resolved:
            resolved.append(value)
    return resolved


def _extract_flow_edges(sections: dict[str, str], repo: Path) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for section, body in sections.items():
        section_root = _section_root(repo, section)
        for line in body.splitlines():
            if "→" not in line:
                continue
            segments = line.split("→")
            resolved = _extract_files(line, repo, section_root)
            counts = [
                sum(1 for token in _CODE.findall(segment) if _is_file_token(token))
                for segment in segments
            ]
            groups: list[list[str]] = []
            offset = 0
            for count in counts:
                groups.append(resolved[offset : offset + count])
                offset += count
            for sources, targets in pairwise(groups):
                edges.extend(
                    (source, target) for source in sources for target in targets
                )
    return edges


def _is_file_token(token: str) -> bool:
    candidate = token.strip().rstrip(".,;:")
    return bool(
        not candidate.startswith("/")
        and "*" not in candidate
        and _FILE_TOKEN.search(candidate)
    )
