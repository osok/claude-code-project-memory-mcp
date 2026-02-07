/**
 * Global Error Handler Middleware
 *
 * Catches and formats all errors for consistent API responses.
 */
import { Request, Response, NextFunction } from 'express';
import { ZodError } from 'zod';
import { v4 as uuidv4 } from 'uuid';

export interface ApiError extends Error {
  statusCode?: number;
  code?: string;
}

export interface ErrorResponse {
  error: {
    message: string;
    code: string;
    requestId: string;
    details?: unknown;
  };
}

export function errorHandler(
  err: ApiError,
  req: Request,
  res: Response,
  _next: NextFunction
): void {
  const requestId = uuidv4();

  // Log error with details
  console.error(`[${requestId}] Error:`, {
    method: req.method,
    path: req.path,
    error: err.message,
    stack: err.stack
  });

  // Determine status code and error code
  let statusCode = err.statusCode || 500;
  let code = err.code || 'INTERNAL_ERROR';
  let message = err.message || 'An unexpected error occurred';
  let details: unknown = undefined;

  // Handle Zod validation errors
  if (err instanceof ZodError) {
    statusCode = 400;
    code = 'VALIDATION_ERROR';
    message = 'Request validation failed';
    details = err.errors.map(e => ({
      path: e.path.join('.'),
      message: e.message
    }));
  }

  // Handle specific error types
  if (err.message?.includes('not found') || err.message?.includes('Not found')) {
    statusCode = 404;
    code = 'NOT_FOUND';
  }

  if (err.message?.includes('already exists') || err.message?.includes('duplicate')) {
    statusCode = 409;
    code = 'CONFLICT';
  }

  if (err.message?.includes('connection') || err.message?.includes('ECONNREFUSED')) {
    statusCode = 503;
    code = 'SERVICE_UNAVAILABLE';
    message = 'Database connection error. Please ensure Qdrant and Neo4j are running.';
  }

  const response: ErrorResponse = {
    error: {
      message,
      code,
      requestId,
      ...(details && { details })
    }
  };

  res.status(statusCode).json(response);
}

/**
 * Create an API error with status code
 */
export function createError(message: string, statusCode: number, code?: string): ApiError {
  const error = new Error(message) as ApiError;
  error.statusCode = statusCode;
  error.code = code;
  return error;
}
