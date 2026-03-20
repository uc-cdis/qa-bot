{{/*
Return the fully qualified app name
*/}}
{{- define "anythingllm.fullname" -}}
{{- printf "%s" .Release.Name -}}
{{- end }}
