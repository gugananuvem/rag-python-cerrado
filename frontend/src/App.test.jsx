import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App.jsx";

describe("App - RAG chat", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra o painel de configuração quando não há endpoint salvo", () => {
    render(<App />);
    expect(screen.getByLabelText(/API Endpoint/i)).toBeInTheDocument();
  });

  it("salva o endpoint no localStorage", () => {
    render(<App />);
    const input = screen.getByPlaceholderText(/execute-api/i);
    fireEvent.change(input, {
      target: { value: "https://api.example.com/chat" },
    });
    fireEvent.click(screen.getByText("Salvar"));
    expect(localStorage.getItem("rag_api_endpoint")).toBe(
      "https://api.example.com/chat"
    );
  });

  it("renderiza o estado vazio com dica inicial", () => {
    localStorage.setItem("rag_api_endpoint", "https://api.example.com/chat");
    render(<App />);
    expect(screen.getByText(/Faça uma pergunta/i)).toBeInTheDocument();
  });

  it("envia a pergunta e exibe a resposta e as fontes", async () => {
    localStorage.setItem("rag_api_endpoint", "https://api.example.com/chat");

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        answer: "RAG é uma técnica de recuperação aumentada.",
        sources: [{ id: "post-001", title: "O que é RAG", score: 0.82 }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const input = screen.getByPlaceholderText(/Digite sua pergunta/i);
    fireEvent.change(input, { target: { value: "O que é RAG?" } });
    fireEvent.click(screen.getByText("Enviar"));

    // mensagem do usuário aparece
    expect(screen.getByText("O que é RAG?")).toBeInTheDocument();

    // resposta do assistente
    await waitFor(() =>
      expect(
        screen.getByText(/técnica de recuperação aumentada/i)
      ).toBeInTheDocument()
    );

    // fonte renderizada
    expect(screen.getByText(/O que é RAG · 0.82/)).toBeInTheDocument();

    // payload enviado corretamente
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question: "O que é RAG?" }),
      })
    );
  });

  it("exibe mensagem de erro quando a API falha", async () => {
    localStorage.setItem("rag_api_endpoint", "https://api.example.com/chat");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        text: async () => "erro interno",
      })
    );

    render(<App />);
    const input = screen.getByPlaceholderText(/Digite sua pergunta/i);
    fireEvent.change(input, { target: { value: "falha?" } });
    fireEvent.click(screen.getByText("Enviar"));

    await waitFor(() =>
      expect(screen.getByText(/Erro:/i)).toBeInTheDocument()
    );
  });

  it("não envia pergunta vazia", () => {
    localStorage.setItem("rag_api_endpoint", "https://api.example.com/chat");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByText("Enviar"));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
