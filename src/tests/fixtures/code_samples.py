"""Sample code for testing language extractors."""

SAMPLE_PYTHON_CODE = '''"""Sample Python module for testing."""

import os
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration dataclass."""

    host: str = "localhost"
    port: int = 8080
    debug: bool = False


class UserService:
    """Service for managing users."""

    def __init__(self, config: Config) -> None:
        """Initialize with config."""
        self.config = config
        self._cache: dict[str, Any] = {}

    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get a user by ID.

        Args:
            user_id: The user identifier

        Returns:
            User data or None if not found
        """
        if user_id in self._cache:
            return self._cache[user_id]
        return None

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email and "." in email

    @property
    def cache_size(self) -> int:
        """Return cache size."""
        return len(self._cache)


def process_data(data: list[dict], *args, **kwargs) -> list[dict]:
    """Process a list of data items.

    Args:
        data: List of dictionaries to process
        *args: Additional positional arguments
        **kwargs: Additional keyword arguments

    Returns:
        Processed data list
    """
    return [item for item in data if item.get("valid")]


async def fetch_resource(url: str, timeout: int = 30) -> bytes:
    """Fetch a resource from URL."""
    return b""
'''

SAMPLE_TYPESCRIPT_CODE = '''/**
 * Sample TypeScript module for testing.
 */

import { Request, Response } from 'express';
import * as fs from 'fs';
import { Config } from './config';

/**
 * User interface definition.
 */
interface User {
    id: string;
    name: string;
    email: string;
    createdAt: Date;
}

/**
 * Base service class.
 */
abstract class BaseService {
    protected config: Config;

    constructor(config: Config) {
        this.config = config;
    }

    abstract initialize(): Promise<void>;
}

/**
 * Service for managing users.
 */
export class UserService extends BaseService implements Disposable {
    private cache: Map<string, User> = new Map();

    constructor(config: Config) {
        super(config);
    }

    async initialize(): Promise<void> {
        console.log('Initializing user service');
    }

    /**
     * Get a user by ID.
     * @param userId - The user identifier
     * @returns The user or undefined
     */
    async getUser(userId: string): Promise<User | undefined> {
        return this.cache.get(userId);
    }

    static validateEmail(email: string): boolean {
        return email.includes('@') && email.includes('.');
    }

    get cacheSize(): number {
        return this.cache.size;
    }

    [Symbol.dispose](): void {
        this.cache.clear();
    }
}

/**
 * Process data items.
 */
export const processData = async <T extends { valid?: boolean }>(
    items: T[],
    options?: { filter?: boolean }
): Promise<T[]> => {
    if (options?.filter) {
        return items.filter(item => item.valid);
    }
    return items;
};

export function createHandler(service: UserService): (req: Request, res: Response) => void {
    return (req, res) => {
        res.json({ status: 'ok' });
    };
}
'''

SAMPLE_JAVASCRIPT_CODE = '''/**
 * Sample JavaScript module for testing.
 */

const fs = require('fs');
const { EventEmitter } = require('events');

/**
 * User service class.
 */
class UserService extends EventEmitter {
    /**
     * Create a new user service.
     * @param {Object} config - Configuration options
     */
    constructor(config) {
        super();
        this.config = config;
        this.cache = new Map();
    }

    /**
     * Get a user by ID.
     * @param {string} userId - The user identifier
     * @returns {Promise<Object|null>} The user or null
     */
    async getUser(userId) {
        if (this.cache.has(userId)) {
            return this.cache.get(userId);
        }
        return null;
    }

    /**
     * Validate email format.
     * @param {string} email - Email to validate
     * @returns {boolean} True if valid
     */
    static validateEmail(email) {
        return email.includes('@') && email.includes('.');
    }

    get cacheSize() {
        return this.cache.size;
    }
}

/**
 * Process data items.
 * @param {Array} items - Items to process
 * @param {Object} options - Processing options
 * @returns {Array} Processed items
 */
const processData = async (items, options = {}) => {
    if (options.filter) {
        return items.filter(item => item.valid);
    }
    return items;
};

function createHandler(service) {
    return function handler(req, res) {
        res.json({ status: 'ok' });
    };
}

module.exports = {
    UserService,
    processData,
    createHandler,
};
'''

SAMPLE_JAVA_CODE = '''/**
 * Sample Java class for testing.
 */
package com.example.service;

import java.util.Map;
import java.util.HashMap;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

/**
 * Service for managing users.
 */
@Service
public class UserService implements Closeable {
    private final Config config;
    private final Map<String, User> cache = new HashMap<>();

    /**
     * Create a new user service.
     * @param config Configuration options
     */
    public UserService(Config config) {
        this.config = config;
    }

    /**
     * Get a user by ID.
     * @param userId The user identifier
     * @return Optional containing user or empty
     */
    public Optional<User> getUser(String userId) {
        return Optional.ofNullable(cache.get(userId));
    }

    /**
     * Get a user asynchronously.
     * @param userId The user identifier
     * @return CompletableFuture with the user
     */
    public CompletableFuture<User> getUserAsync(String userId) {
        return CompletableFuture.supplyAsync(() -> cache.get(userId));
    }

    /**
     * Validate email format.
     * @param email Email to validate
     * @return true if valid
     */
    public static boolean validateEmail(String email) {
        return email.contains("@") && email.contains(".");
    }

    /**
     * Get cache size.
     * @return Number of cached items
     */
    public int getCacheSize() {
        return cache.size();
    }

    @Override
    public void close() {
        cache.clear();
    }

    /**
     * Process data with variable args.
     * @param items Items to process
     * @return Processed items
     */
    public User[] processUsers(User... items) {
        return items;
    }
}

/**
 * User interface.
 */
interface Identifiable {
    String getId();
}
'''

SAMPLE_GO_CODE = '''// Package service provides user management functionality.
package service

import (
    "context"
    "errors"
    "sync"
)

// User represents a user in the system.
type User struct {
    ID    string
    Name  string
    Email string
}

// Validator interface for validation.
type Validator interface {
    Validate() error
}

// UserService manages users.
type UserService struct {
    config *Config
    cache  map[string]*User
    mu     sync.RWMutex
}

// NewUserService creates a new user service.
func NewUserService(config *Config) *UserService {
    return &UserService{
        config: config,
        cache:  make(map[string]*User),
    }
}

// GetUser retrieves a user by ID.
func (s *UserService) GetUser(ctx context.Context, userID string) (*User, error) {
    s.mu.RLock()
    defer s.mu.RUnlock()

    user, ok := s.cache[userID]
    if !ok {
        return nil, errors.New("user not found")
    }
    return user, nil
}

// SetUser stores a user in the cache.
func (s *UserService) SetUser(user *User) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.cache[user.ID] = user
}

// CacheSize returns the number of cached users.
func (s *UserService) CacheSize() int {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return len(s.cache)
}

// ValidateEmail checks if an email is valid.
func ValidateEmail(email string) bool {
    return len(email) > 0 && contains(email, "@") && contains(email, ".")
}

func contains(s, substr string) bool {
    return len(s) > 0 && len(substr) > 0
}

// ProcessUsers processes a variable number of users.
func ProcessUsers(users ...*User) []*User {
    result := make([]*User, 0, len(users))
    for _, u := range users {
        if u != nil {
            result = append(result, u)
        }
    }
    return result
}
'''

SAMPLE_RUST_CODE = '''//! Sample Rust module for testing.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::error::Error;

/// User represents a user in the system.
#[derive(Debug, Clone)]
pub struct User {
    pub id: String,
    pub name: String,
    pub email: String,
}

/// Validator trait for validation.
pub trait Validator {
    /// Validate the object.
    fn validate(&self) -> Result<(), Box<dyn Error>>;
}

impl Validator for User {
    fn validate(&self) -> Result<(), Box<dyn Error>> {
        if self.email.contains('@') {
            Ok(())
        } else {
            Err("Invalid email".into())
        }
    }
}

/// Configuration for the service.
#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
}

/// Service for managing users.
pub struct UserService {
    config: Config,
    cache: Arc<RwLock<HashMap<String, User>>>,
}

impl UserService {
    /// Create a new user service.
    pub fn new(config: Config) -> Self {
        Self {
            config,
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get a user by ID.
    pub fn get_user(&self, user_id: &str) -> Option<User> {
        let cache = self.cache.read().ok()?;
        cache.get(user_id).cloned()
    }

    /// Set a user in the cache.
    pub fn set_user(&self, user: User) -> Result<(), &'static str> {
        let mut cache = self.cache.write().map_err(|_| "Lock error")?;
        cache.insert(user.id.clone(), user);
        Ok(())
    }

    /// Get the cache size.
    pub fn cache_size(&self) -> usize {
        self.cache.read().map(|c| c.len()).unwrap_or(0)
    }
}

/// Validate an email address.
pub fn validate_email(email: &str) -> bool {
    email.contains('@') && email.contains('.')
}

/// Process users asynchronously.
pub async fn process_users(users: Vec<User>) -> Vec<User> {
    users.into_iter().filter(|u| !u.email.is_empty()).collect()
}
'''

SAMPLE_CSHARP_CODE = '''/// <summary>
/// Sample C# class for testing.
/// </summary>

using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Example.Service
{
    /// <summary>
    /// User model.
    /// </summary>
    public class User
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public string Email { get; set; }
    }

    /// <summary>
    /// Validator interface.
    /// </summary>
    public interface IValidator
    {
        bool Validate();
    }

    /// <summary>
    /// Service for managing users.
    /// </summary>
    [Service]
    public class UserService : IDisposable, IValidator
    {
        private readonly Config _config;
        private readonly Dictionary<string, User> _cache = new();

        /// <summary>
        /// Create a new user service.
        /// </summary>
        /// <param name="config">Configuration options.</param>
        public UserService(Config config)
        {
            _config = config;
        }

        /// <summary>
        /// Get a user by ID.
        /// </summary>
        /// <param name="userId">The user identifier.</param>
        /// <returns>The user or null.</returns>
        public User GetUser(string userId)
        {
            return _cache.TryGetValue(userId, out var user) ? user : null;
        }

        /// <summary>
        /// Get a user asynchronously.
        /// </summary>
        public async Task<User> GetUserAsync(string userId)
        {
            await Task.Delay(1);
            return GetUser(userId);
        }

        /// <summary>
        /// Validate email format.
        /// </summary>
        public static bool ValidateEmail(string email)
        {
            return email.Contains("@") && email.Contains(".");
        }

        /// <summary>
        /// Cache size property.
        /// </summary>
        public int CacheSize => _cache.Count;

        /// <summary>
        /// Validate the service.
        /// </summary>
        public bool Validate()
        {
            return _config != null;
        }

        /// <summary>
        /// Dispose resources.
        /// </summary>
        public void Dispose()
        {
            _cache.Clear();
        }

        /// <summary>
        /// Process users with params.
        /// </summary>
        public User[] ProcessUsers(params User[] users)
        {
            return users;
        }
    }
}
'''
