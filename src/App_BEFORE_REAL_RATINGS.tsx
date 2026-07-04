import React from "react";

const tabs = ["Worksheet", "Ratings", "Form", "Speed Map", "Performance", "Results", "Bets"];

export default function App(): React.ReactElement {
  return (
    <div className="min-h-screen bg-[#0f0f10] text-white">
      <div className="mx-auto max-w-[1600px] px-4 py-5">
        <div className="rounded-md border border-[#2a2a2a] bg-[#151515] shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
          <div className="border-b border-[#262626] bg-[linear-gradient(180deg,#1d1d1d_0%,#141414_100%)] px-5 py-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-[#8e8e8e]">
                  EDGEiQ RACING
                </div>
                <div className="mt-1 text-[30px] font-semibold tracking-tight text-[#f4f4f4]">
                  Live Race Analysis
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="rounded-sm border border-[#303030] bg-[#202020] px-3 py-2 text-[11px] text-[#d2d2d2]">
                  Today
                </div>
                <div className="rounded-sm border border-[#303030] bg-[#202020] px-3 py-2 text-[11px] text-[#d2d2d2]">
                  Future
                </div>
                <div className="rounded-sm border border-[#6d5722] bg-[#6d5722] px-3 py-2 text-[11px] font-medium text-white">
                  Ratings Engine Live
                </div>
              </div>
            </div>
          </div>

          <div className="border-b border-[#262626] bg-[#121212] px-5 py-3">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-[2fr_1fr_1fr_1fr]">
              <div>
                <div className="mb-1 text-[10px] uppercase tracking-[0.16em] text-[#808080]">
                  Meeting / Race
                </div>
                <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-3 text-[14px] text-[#f2f2f2]">
                  Caulfield  Race 6  1400m  BM78
                </div>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Winning Figure</div>
                <div className="mt-1 text-[22px] font-semibold text-[#f5f5f5]">98.4</div>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Top Rated</div>
                <div className="mt-1 text-[16px] font-semibold text-[#f5f5f5]">Runner Name</div>
              </div>

              <div className="rounded-sm border border-[#2f2f2f] bg-[#1d1d1d] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.16em] text-[#808080]">Runners</div>
                <div className="mt-1 text-[22px] font-semibold text-[#f5f5f5]">12</div>
              </div>
            </div>
          </div>

          <div className="border-b border-[#262626] bg-[#171717] px-5 py-2">
            <div className="flex flex-wrap items-center gap-2">
              {tabs.map((tab, index) => (
                <button
                  key={tab}
                  className={
                    index === 1
                      ? "rounded-sm border border-[#725a21] bg-[#725a21] px-3 py-1.5 text-[13px] font-medium text-white"
                      : "rounded-sm border border-[#303030] bg-[#222222] px-3 py-1.5 text-[13px] text-[#d3d3d3]"
                  }
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          <div className="px-5 py-5">
            <div className="rounded-md border border-[#2b2b2b] bg-[#111111]">
              <div className="border-b border-[#232323] px-4 py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.18em] text-[#878787]">Ratings Grid</div>
                    <div className="mt-1 text-[20px] font-semibold text-[#f2f2f2]">Form King Style Ratings</div>
                  </div>
                  <div className="text-[12px] text-[#b8b8b8]">This is the new premium shell. Next step is wiring every tab into this style.</div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-[1400px] w-full text-[12px] text-white">
                  <thead>
                    <tr className="border-b border-[#222] bg-[#171717] text-left text-[10px] uppercase tracking-[0.14em] text-[#989898]">
                      <th className="px-3 py-3">Horse</th>
                      <th className="px-3 py-3">Jockey</th>
                      <th className="px-3 py-3">Trainer</th>
                      <th className="px-3 py-3">Bar</th>
                      <th className="px-2 py-3">EXP</th>
                      <th className="px-2 py-3">TODAY</th>
                      <th className="px-2 py-3">LS1</th>
                      <th className="px-2 py-3">LS2</th>
                      <th className="px-2 py-3">LS3</th>
                      <th className="px-2 py-3">LS4</th>
                      <th className="px-2 py-3">LS5</th>
                      <th className="px-3 py-3">Rated</th>
                      <th className="px-3 py-3">Market</th>
                      <th className="px-3 py-3">Rank</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Runner One","J. Allen","Maher",4,"96.4","98.1","94.2","96.0","92.5","95.4","97.0","4.80","5.50","1"],
                      ["Runner Two","D. Lane","Freedman",8,"95.2","97.4","93.4","95.1","91.8","94.8","96.3","5.20","6.00","2"],
                      ["Runner Three","B. Melham","Price",2,"93.8","95.9","91.2","92.7","90.4","91.6","94.0","8.50","9.00","3"],
                    ].map((row, i) => (
                      <tr key={i} className="border-b border-[#1d1d1d] bg-[#121212] hover:bg-[#181818]">
                        <td className="px-3 py-3 font-semibold">{row[0]}</td>
                        <td className="px-3 py-3 text-[#d0d0d0]">{row[1]}</td>
                        <td className="px-3 py-3 text-[#d0d0d0]">{row[2]}</td>
                        <td className="px-3 py-3">{row[3]}</td>
                        {[4,5,6,7,8,9,10].map((idx) => (
                          <td key={idx} className="px-2 py-2">
                            <div className="flex h-[38px] w-[52px] items-center justify-center rounded-sm border border-[#3a3a3a] bg-[#2f8f4e] text-[11px] font-semibold text-white">
                              {row[idx]}
                            </div>
                          </td>
                        ))}
                        <td className="px-3 py-3 font-semibold">{row[11]}</td>
                        <td className="px-3 py-3 text-[#cfcfcf]">{row[12]}</td>
                        <td className="px-3 py-3 text-[#9b9b9b]">{row[13]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

