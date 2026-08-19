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

service_anchor = '''    .then(([windowModel, catalog]) => {
      const viewModel: MeetingsWorkspaceViewModel = {
'''

service_replacement = '''    .then(([windowModel, catalog]) => {
      console.info("EDGEIQ_MEETINGS_SERVICE_TRACE", {
        windowDates: windowModel.dates,
        windowDateCount: windowModel.dates?.length ?? null,
        catalogDates: catalog.dates,
        catalogMeetingCount: catalog.meetings?.length ?? null,
      });

      const viewModel: MeetingsWorkspaceViewModel = {
'''

if "EDGEIQ_MEETINGS_SERVICE_TRACE" not in service_text:
    if service_anchor not in service_text:
        raise RuntimeError(
            "Service instrumentation anchor was not found. "
            "No file was modified."
        )
    service_text = service_text.replace(
        service_anchor,
        service_replacement,
        1,
    )

service_return_anchor = '''      cachedViewModel = viewModel;
      return viewModel;
'''

service_return_replacement = '''      console.info("EDGEIQ_MEETINGS_VIEWMODEL_TRACE", {
        status: viewModel.status,
        dayCount: viewModel.days.length,
        days: viewModel.days.map((day) => ({
          key: day.key,
          date: day.date,
          meetings: day.meetings.length,
          races: day.totals.races,
        })),
      });

      cachedViewModel = viewModel;
      return viewModel;
'''

if "EDGEIQ_MEETINGS_VIEWMODEL_TRACE" not in service_text:
    if service_return_anchor not in service_text:
        raise RuntimeError(
            "Service return instrumentation anchor was not found. "
            "No file was modified."
        )
    service_text = service_text.replace(
        service_return_anchor,
        service_return_replacement,
        1,
    )

component_success_anchor = '''      .then((nextViewModel) => {
        if (!active) return;
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch(() => {
        if (!active) return;
        setStatus("ERROR");
      });
'''

component_success_replacement = '''      .then((nextViewModel) => {
        console.info("EDGEIQ_MEETINGS_COMPONENT_SUCCESS", {
          active,
          selectedDayKey,
          dayCount: nextViewModel.days.length,
          days: nextViewModel.days.map((day) => ({
            key: day.key,
            date: day.date,
            meetings: day.meetings.length,
          })),
        });

        if (!active) return;
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch((error) => {
        console.error("EDGEIQ_MEETINGS_COMPONENT_ERROR", error);
        if (!active) return;
        setStatus("ERROR");
      });
'''

if "EDGEIQ_MEETINGS_COMPONENT_SUCCESS" not in component_text:
    if component_success_anchor not in component_text:
        raise RuntimeError(
            "Component lifecycle instrumentation anchor was not found. "
            "No file was modified."
        )
    component_text = component_text.replace(
        component_success_anchor,
        component_success_replacement,
        1,
    )

manual_load_anchor = '''    loadMeetingsWorkspaceViewModel(force)
      .then((nextViewModel) => {
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch(() => {
        setStatus("ERROR");
      });
'''

manual_load_replacement = '''    loadMeetingsWorkspaceViewModel(force)
      .then((nextViewModel) => {
        console.info("EDGEIQ_MEETINGS_MANUAL_LOAD_SUCCESS", {
          force,
          dayCount: nextViewModel.days.length,
        });
        setViewModel(nextViewModel);
        setStatus("READY");
      })
      .catch((error) => {
        console.error("EDGEIQ_MEETINGS_MANUAL_LOAD_ERROR", error);
        setStatus("ERROR");
      });
'''

if "EDGEIQ_MEETINGS_MANUAL_LOAD_SUCCESS" not in component_text:
    if manual_load_anchor not in component_text:
        raise RuntimeError(
            "Component manual-load instrumentation anchor was not found. "
            "No file was modified."
        )
    component_text = component_text.replace(
        manual_load_anchor,
        manual_load_replacement,
        1,
    )

service_path.write_text(service_text, encoding="utf-8")
component_path.write_text(component_text, encoding="utf-8")

print("EDGEIQ_MEETINGS_PIPELINE_TRACE_V1_APPLIED")
print(f"service={service_path}")
print(f"component={component_path}")
