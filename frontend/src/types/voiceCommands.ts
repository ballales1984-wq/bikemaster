/**
 * Voice command system types.
 *
 * Defines interfaces for voice commands, their parameters,
 * execution results, and the recognition state machine.
 */

export type CommandDomain =
  | "navigation"
  | "athlete"
  | "calendar"
  | "rides"
  | "nutrition"
  | "tracking"
  | "settings"
  | "system"
  | "connections"
  | "import"
  | "maps"
  | "badges"
  | "weather"
  | "knowledge"
  | "bm2"
  | "granfondo"
  | "sync"
  | "metabolism";

export type ParameterType =
  | "string"
  | "number"
  | "date"
  | "time"
  | "datetime"
  | "enum"
  | "boolean"
  | "meal_type"
  | "event_type"
  | "activity_type";

export interface VoiceCommandParameter {
  name: string;
  type: ParameterType;
  required: boolean;
  description: string;
  aliases?: string[];
  enumValues?: string[];
}

export interface VoiceCommandDefinition {
  id: string;
  domain: CommandDomain;
  label: string;
  description: string;
  examples: string[];
  triggerWords: string[];
  parameters: VoiceCommandParameter[];
  execute: (params: Record<string, unknown>) => Promise<VoiceCommandResult>;
}

export interface VoiceCommandResult {
  success: boolean;
  message: string;
  data?: unknown;
}

export interface ParsedCommand {
  definition: VoiceCommandDefinition;
  params: Record<string, unknown>;
  rawTranscript: string;
  confidence: number;
}

export interface RecognitionState {
  isListening: boolean;
  isProcessing: boolean;
  lastTranscript: string;
  lastResult: VoiceCommandResult | null;
  error: string | null;
  supported: boolean;
}

export interface VoiceCommandLogEntry {
  id: string;
  timestamp: Date;
  transcript: string;
  commandId: string | null;
  success: boolean;
  message: string;
  params: Record<string, unknown>;
}
