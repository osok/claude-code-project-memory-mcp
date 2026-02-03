import { logger } from "../utils/logger.js";

const VOYAGE_BASE_URL = "https://api.voyageai.com/v1";
const MODEL = "voyage-code-3";
const MAX_BATCH_SIZE = 100;

interface EmbeddingResponse {
  data: Array<{
    embedding: number[];
    index: number;
  }>;
  usage: {
    total_tokens: number;
  };
}

export class VoyageClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async embed(text: string): Promise<number[]> {
    const embeddings = await this.embedBatch([text]);
    const result = embeddings[0];
    if (!result) {
      throw new Error("No embedding returned");
    }
    return result;
  }

  async embedBatch(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) {
      return [];
    }

    if (texts.length > MAX_BATCH_SIZE) {
      // Split into chunks
      const results: number[][] = [];
      for (let i = 0; i < texts.length; i += MAX_BATCH_SIZE) {
        const chunk = texts.slice(i, i + MAX_BATCH_SIZE);
        const chunkResults = await this.embedBatch(chunk);
        results.push(...chunkResults);
      }
      return results;
    }

    const response = await fetch(`${VOYAGE_BASE_URL}/embeddings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        model: MODEL,
        input: texts
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      logger.error("Voyage API error", { status: response.status, error: errorText });
      throw new Error(`Voyage API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json() as EmbeddingResponse;

    // Sort by index to maintain order
    const sorted = data.data.sort((a, b) => a.index - b.index);
    return sorted.map(d => d.embedding);
  }
}
