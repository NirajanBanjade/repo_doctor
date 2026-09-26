import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import ApprovalModal from "./ApprovalModal";

describe("ApprovalModal", () => {
  it("renders title and message", () => {
    render(
      <ApprovalModal
        title="Confirm action"
        message="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Confirm action")).toBeInTheDocument();
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
  });

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ApprovalModal
        title="T"
        message="M"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Confirm"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = vi.fn();
    render(
      <ApprovalModal
        title="T"
        message="M"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("calls onCancel when Escape key pressed", () => {
    const onCancel = vi.fn();
    render(
      <ApprovalModal
        title="T"
        message="M"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables buttons when isLoading is true", () => {
    render(
      <ApprovalModal
        title="T"
        message="M"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        isLoading
      />,
    );
    expect(screen.getByText("Working…")).toBeDisabled();
    expect(screen.getByText("Cancel")).toBeDisabled();
  });

  it("uses custom confirmLabel and cancelLabel", () => {
    render(
      <ApprovalModal
        title="T"
        message="M"
        confirmLabel="Delete"
        cancelLabel="Go back"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Delete")).toBeInTheDocument();
    expect(screen.getByText("Go back")).toBeInTheDocument();
  });
});
