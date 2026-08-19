from pathlib import Path

ROOT = Path(r"C:\Users\trent\OneDrive\Documents\EDGEIQ_PLATFORM")

service_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "services"
    / "meetingsFeed.ts"
)

component_path = (
    ROOT
    / "src"
    / "edgeiq-os"
    / "race"
    / "components"
    / "MeetingsWorkspace.tsx"
)

service_text = service_path.read_text(encoding="utf-8")
component_text = component_path.read_text(encoding="utf-8")

service_trace = '''      console.info("EDGEIQ_MEETINGS_SERVICE_TRACE", {
        windowDates: windowModel.dates,
        windowDateCount: windowModel.dates?.length ?? null,
        catalogDates: catalog.dates,
        catalogMeetingCount: catalog.meetings?.length ?? null,
      });

'''

service_viewmodel_trace = '''      console.info("EDGEIQ_MEETINGS_VIEWMODEL_TRACE", {
        status: viewModel.status,
        dayCount: viewModel.days.length,
        days: viewModel.days.map((day) => ({
          key: day.key,
          date: day.date,
          meetings: day.meetings.length,
          races: day.totals.races,
        })),
      });

'''

component_effect_trace = '''        console.info("EDGEIQ_MEETINGS_COMPONENT_SUCCESS", {
          active,
          selectedDayKey,
          dayCount: nextViewModel.days.length,
          days: nextViewModel.days.map((day) => ({
            key: day.key,
            date: day.date,
            meetings: day.meetings.length,
          })),
        });

'''

component_manual_trace = '''        console.info("EDGEIQ_MEETINGS_MANUAL_LOAD_SUCCESS", {
          force,
          dayCount: nextViewModel.days.length,
        });
'''

service_text = service_text.replace(service_trace, "", 1)
service_text = service_text.replace(service_viewmodel_trace, "", 1)
component_text = component_text.replace(component_effect_trace, "", 1)
component_text = component_text.replace(component_manual_trace, "", 1)

component_text = component_text.replace(
    '''      .catch((error) => {
        console.error("EDGEIQ_MEETINGS_MANUAL_LOAD_ERROR", error);
        setStatus("ERROR");
      });
''',
    '''      .catch(() => {
        setStatus("ERROR");
      });
''',
    1,
)

component_text = component_text.replace(
    '''      .catch((error) => {
        console.error("EDGEIQ_MEETINGS_COMPONENT_ERROR", error);
        if (!active) return;
        setStatus("ERROR");
      });
''',
    '''      .catch(() => {
        if (!active) return;
        setStatus("ERROR");
      });
''',
    1,
)

service_path.write_text(service_text, encoding="utf-8")
component_path.write_text(component_text, encoding="utf-8")

print("EDGEIQ_MEETINGS_POST_RECOVERY_TRACE_CLEANUP_COMPLETE")
