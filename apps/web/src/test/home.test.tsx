import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import HomePage from "../app/page";

it("renders the product identity", () => {
  render(<HomePage />);
  expect(screen.getByRole("heading", { name: "Personal PM Agent" })).toBeVisible();
});
