import { app } from "../../../scripts/app.js";

app.registerExtension({
  name: "Anima.Apps.WorkflowList",
  async setup() {
    // Mobile App Mode only lists open workflows. Register the installed apps
    // in that native list so a new phone can select every app immediately.
    const workflows = app.extensionManager.workflow;
    const paths = workflows.persistedWorkflows
      .filter((workflow) => workflow.path.startsWith("workflows/Anima Apps/") && workflow.path.endsWith(".app.json"))
      .map((workflow) => workflow.path)
      .sort();
    workflows.openWorkflowsInBackground({ right: paths });
  },
});
