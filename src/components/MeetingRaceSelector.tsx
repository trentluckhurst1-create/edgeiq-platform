import React from "react";

type MeetingOption = {
  key: string;
  label: string;
};

type RaceButton = {
  key: string;
  raceNo: number;
  label: string;
};

type Props = {
  meetingOptions: MeetingOption[];
  selectedMeetingKey: string;
  onSelectMeeting: (meetingKey: string) => void;
  raceButtons: RaceButton[];
  selectedRaceKey: string;
  onSelectRace: (raceKey: string) => void;
};

export default function MeetingRaceSelector({
  meetingOptions,
  selectedMeetingKey,
  onSelectMeeting,
  raceButtons,
  selectedRaceKey,
  onSelectRace,
}: Props) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-3 min-w-[460px] shadow-lg">
      <div className="text-[11px] uppercase tracking-widest text-slate-500">
        Meeting selector
      </div>

      <select
        className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
        value={selectedMeetingKey}
        onChange={(e) => onSelectMeeting(e.target.value)}
      >
        {meetingOptions.map((option) => (
          <option key={option.key} value={option.key}>
            {option.label}
          </option>
        ))}
      </select>

      <div className="mt-3 flex flex-wrap gap-2">
        {raceButtons.map((race) => {
          const active = race.key === selectedRaceKey;
          return (
            <button
              key={race.key}
              type="button"
              onClick={() => onSelectRace(race.key)}
              className={`rounded-xl px-3 py-1.5 text-sm font-semibold transition ${
                active
                  ? "bg-[#07101d] text-slate-950 shadow"
                  : "border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {race.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

