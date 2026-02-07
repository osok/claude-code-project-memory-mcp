/**
 * Request Logger Middleware
 *
 * Logs incoming requests with method, path, status, and duration.
 */
import { Request, Response, NextFunction } from 'express';

const LOG_LEVEL = process.env.INSPECTOR_LOG_LEVEL || 'info';
const EXCLUDED_PATHS = ['/api/health'];

export function requestLogger(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  // Skip logging for excluded paths
  if (EXCLUDED_PATHS.includes(req.path)) {
    return next();
  }

  const startTime = Date.now();

  // Log on response finish
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    const logMessage = formatLogMessage(req, res, duration);

    if (LOG_LEVEL === 'debug' || res.statusCode >= 400) {
      console.log(logMessage);
    } else if (LOG_LEVEL === 'info') {
      // Only log non-successful responses or slow requests (>1s)
      if (res.statusCode >= 400 || duration > 1000) {
        console.log(logMessage);
      }
    }
  });

  next();
}

function formatLogMessage(req: Request, res: Response, duration: number): string {
  const timestamp = new Date().toISOString();
  const method = req.method.padEnd(7);
  const path = req.path;
  const status = res.statusCode;
  const statusColor = getStatusColor(status);

  return `[${timestamp}] ${method} ${path} ${statusColor}${status}\x1b[0m ${duration}ms`;
}

function getStatusColor(status: number): string {
  if (status < 300) return '\x1b[32m'; // Green
  if (status < 400) return '\x1b[33m'; // Yellow
  if (status < 500) return '\x1b[31m'; // Red
  return '\x1b[35m'; // Magenta
}
