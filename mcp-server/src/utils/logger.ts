type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

function log(level: LogLevel, message: string, data?: unknown): void {
  const entry = {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...(data ? { data } : {})
  };
  console.error(JSON.stringify(entry));
}

export const logger = {
  debug: (msg: string, data?: unknown) => log("DEBUG", msg, data),
  info: (msg: string, data?: unknown) => log("INFO", msg, data),
  warn: (msg: string, data?: unknown) => log("WARN", msg, data),
  error: (msg: string, data?: unknown) => log("ERROR", msg, data)
};
