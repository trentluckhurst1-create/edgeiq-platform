
export type FeedRow = Record<string, string>;

export interface FeedLoadResult {
  path: string;
  rows: FeedRow[];
  loaded: boolean;
  error?: string;
}
