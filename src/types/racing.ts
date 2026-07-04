export type RaceMarketRow = {
  race_date: string;
  track: string;
  race_no: number;
  horse: string;
  horse_no: number | null;
  barrier: number | null;
  jockey: string;
  trainer: string;
  today_rating: number | null;
  winning_rating: number | null;
  rating_gap: number | null;
  rated_probability: number | null;
  model_probability: number | null;
  rated_price: number | null;
  model_rank: number | null;
};

export type HistoricalFormRow = {
  horse: string;
  race_date: string;
  track: string;
  race_no: number | null;
  distance: number | null;
  track_condition: string;
  barrier: number | null;
  jockey: string;
  trainer: string;
  finish_pos: string;
  margin: number | null;
  sp: number | null;
  run_rating: number | null;
  race_rating: number | null;
};

export type RaceOption = {
  key: string;
  label: string;
  race_date: string;
  track: string;
  race_no: number;
};

export type TabKey =
  | "execution"
  | "market_tape"
  | "ratings"
  | "form"
  | "speed_map"
  | "intelligence"
  | "performance"
  | "bets";
