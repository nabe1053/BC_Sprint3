import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/shared/testing/test-utils";
import { ApiError } from "@/shared/api/mutator";
import { CaseMetadata } from "../CaseMetadata";
import { useCase } from "../../hooks";
jest.mock("../../hooks", () => ({ useCase: jest.fn() }));
const mockUseCase = useCase as jest.Mock;
it("案件メタは実APIの値を表示し、未提供の納期などを推測しない", () => {
  mockUseCase.mockReturnValue({
    data: { caseCode: "REAL", customerName: "Buyer", title: "Inquiry" },
  });
  renderWithProviders(<CaseMetadata caseId={8} />);
  expect(mockUseCase).toHaveBeenCalledWith(8);
  for (const value of ["REAL", "Buyer", "Inquiry"])
    expect(screen.getByText(value)).toBeInTheDocument();
  expect(screen.getAllByText("—")).toHaveLength(3);
  expect(screen.getByText(/納期・納地・見積期限は/)).toBeInTheDocument();
});
it("存在しない案件は一覧への戻り方を示す", () => {
  mockUseCase.mockReturnValue({
    isError: true,
    error: new ApiError(404, { code: "E_CASE_NOT_FOUND" }),
  });
  renderWithProviders(<CaseMetadata caseId={8} />);
  expect(screen.getByRole("alert")).toHaveTextContent(
    "案件一覧から選び直してください",
  );
});
