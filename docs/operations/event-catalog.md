# Telemetry Event Catalog v1

Privacy contract: `document_text`, `oauth_token`, `prompt_text`,
`personal_note`, `calendar_description` are rejected at the emitter
boundary (`SensitiveTelemetryFieldError`). Workspaces appear only as
hashes. All events carry `schema_version`, `trace_id`, `code_version`.

| Event | Dimensions | Source |
|---|---|---|
| PlannerRunEvent | planner_version, input_size, latency_ms, result | PlanningService.create_plan |
| ExternalExecutionEvent | command_type, outcome, attempts | CalendarCommandExecutor |
| UxEvent | name (UX-001..006), duration_ms | web ux-events.ts |
