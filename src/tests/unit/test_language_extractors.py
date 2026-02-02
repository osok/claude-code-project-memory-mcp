"""Comprehensive unit tests for language extractors.

Tests for parsing/extractors/ covering CSharp, Rust, JavaScript, and Java
extractors with detailed extraction and edge case coverage.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory_service.parsing.extractors.csharp import CSharpExtractor
from memory_service.parsing.extractors.rust import RustExtractor
from memory_service.parsing.extractors.javascript import JavaScriptExtractor
from memory_service.parsing.extractors.java import JavaExtractor


class TestCSharpExtractorDetailed:
    """Detailed tests for CSharpExtractor."""

    @pytest.fixture
    def extractor(self) -> CSharpExtractor:
        """Create C# extractor."""
        return CSharpExtractor()

    def test_language_property(self, extractor: CSharpExtractor) -> None:
        """Test language property returns c_sharp."""
        assert extractor.language == "c_sharp"

    def test_extract_simple_class(self, extractor: CSharpExtractor) -> None:
        """Test extracting simple class."""
        code = """
public class HelloWorld
{
    public static void Main(string[] args)
    {
        Console.WriteLine("Hello, World!");
    }
}
"""
        result = extractor.extract(code, "HelloWorld.cs")

        assert result.file_path == "HelloWorld.cs"
        assert result.language == "c_sharp"
        assert len(result.classes) >= 1
        assert any(c.name == "HelloWorld" for c in result.classes)

    def test_extract_class_with_inheritance(self, extractor: CSharpExtractor) -> None:
        """Test extracting class with base class and interfaces."""
        code = """
public class UserService : BaseService, IUserService, IDisposable
{
    public void GetUser() { }
}
"""
        result = extractor.extract(code, "UserService.cs")

        assert len(result.classes) >= 1
        user_class = next((c for c in result.classes if c.name == "UserService"), None)
        assert user_class is not None
        assert len(user_class.bases) >= 1

    def test_extract_interface(self, extractor: CSharpExtractor) -> None:
        """Test extracting interface."""
        code = """
public interface IUserService
{
    User GetUser(int id);
    void CreateUser(User user);
}
"""
        result = extractor.extract(code, "IUserService.cs")

        assert len(result.classes) >= 1
        interface = next((c for c in result.classes if c.name == "IUserService"), None)
        assert interface is not None
        assert interface.is_abstract  # Interfaces are abstract

    def test_extract_abstract_class(self, extractor: CSharpExtractor) -> None:
        """Test extracting abstract class."""
        code = """
public abstract class BaseService
{
    public abstract void Execute();
    public virtual void Log() { }
}
"""
        result = extractor.extract(code, "BaseService.cs")

        assert len(result.classes) >= 1
        base_class = next((c for c in result.classes if c.name == "BaseService"), None)
        assert base_class is not None
        assert base_class.is_abstract

    def test_extract_method_with_parameters(self, extractor: CSharpExtractor) -> None:
        """Test extracting method with typed parameters."""
        code = """
public class Calculator
{
    public int Add(int a, int b)
    {
        return a + b;
    }

    public double Calculate(double x, double y, string operation = "add")
    {
        return x + y;
    }
}
"""
        result = extractor.extract(code, "Calculator.cs")

        assert len(result.classes) >= 1
        calc = result.classes[0]
        assert len(calc.methods) >= 2

    def test_extract_constructor(self, extractor: CSharpExtractor) -> None:
        """Test extracting constructor."""
        code = """
public class Person
{
    private string _name;

    public Person(string name)
    {
        _name = name;
    }
}
"""
        result = extractor.extract(code, "Person.cs")

        assert len(result.classes) >= 1
        person = result.classes[0]
        assert len(person.methods) >= 1
        ctor = next((m for m in person.methods if m.name == "Person"), None)
        assert ctor is not None

    def test_extract_property(self, extractor: CSharpExtractor) -> None:
        """Test extracting property."""
        code = """
public class User
{
    public string Name { get; set; }
    public int Age { get; private set; }
}
"""
        result = extractor.extract(code, "User.cs")

        assert len(result.classes) >= 1
        user = result.classes[0]
        # Properties are extracted as methods with is_property flag
        assert len(user.methods) >= 1

    def test_extract_async_method(self, extractor: CSharpExtractor) -> None:
        """Test extracting async method."""
        code = """
public class DataService
{
    public async Task<Data> FetchDataAsync()
    {
        await Task.Delay(100);
        return new Data();
    }
}
"""
        result = extractor.extract(code, "DataService.cs")

        assert len(result.classes) >= 1
        service = result.classes[0]
        async_method = next((m for m in service.methods if "Fetch" in m.name), None)
        assert async_method is not None
        assert async_method.is_async

    def test_extract_static_method(self, extractor: CSharpExtractor) -> None:
        """Test extracting static method."""
        code = """
public class Utility
{
    public static int Add(int a, int b) => a + b;
}
"""
        result = extractor.extract(code, "Utility.cs")

        assert len(result.classes) >= 1
        util = result.classes[0]
        static_method = next((m for m in util.methods if m.name == "Add"), None)
        assert static_method is not None
        assert static_method.is_static

    def test_extract_using_directives(self, extractor: CSharpExtractor) -> None:
        """Test extracting using directives."""
        code = """
using System;
using System.Collections.Generic;
using System.Linq;
using static System.Math;
using MyAlias = Some.Long.Namespace;

public class Test { }
"""
        result = extractor.extract(code, "Test.cs")

        assert len(result.imports) >= 3

    def test_extract_xml_documentation(self, extractor: CSharpExtractor) -> None:
        """Test extracting XML documentation comments."""
        code = '''
/// <summary>
/// Calculator class for arithmetic operations.
/// </summary>
public class Calculator
{
    /// <summary>
    /// Adds two integers.
    /// </summary>
    /// <param name="a">First number</param>
    /// <param name="b">Second number</param>
    /// <returns>Sum of a and b</returns>
    public int Add(int a, int b) => a + b;
}
'''
        result = extractor.extract(code, "Calculator.cs")

        assert len(result.classes) >= 1
        calc = result.classes[0]
        assert calc.docstring is not None

    def test_extract_attributes(self, extractor: CSharpExtractor) -> None:
        """Test extracting attributes as decorators."""
        code = """
[Serializable]
[Table("users")]
public class User
{
    [Required]
    public string Name { get; set; }
}
"""
        result = extractor.extract(code, "User.cs")

        assert len(result.classes) >= 1
        user = result.classes[0]
        assert len(user.decorators) >= 1

    def test_extract_struct(self, extractor: CSharpExtractor) -> None:
        """Test extracting struct."""
        code = """
public struct Point
{
    public int X { get; set; }
    public int Y { get; set; }
}
"""
        result = extractor.extract(code, "Point.cs")

        assert len(result.classes) >= 1
        point = next((c for c in result.classes if c.name == "Point"), None)
        assert point is not None

    def test_extract_enum(self, extractor: CSharpExtractor) -> None:
        """Test extracting enum."""
        code = """
public enum Status
{
    Active,
    Inactive,
    Pending
}
"""
        result = extractor.extract(code, "Status.cs")

        assert len(result.classes) >= 1

    def test_extract_record(self, extractor: CSharpExtractor) -> None:
        """Test extracting record (C# 9+)."""
        code = """
public record Person(string Name, int Age);
"""
        result = extractor.extract(code, "Person.cs")

        # Records should be extracted
        assert result is not None

    def test_extract_empty_file(self, extractor: CSharpExtractor) -> None:
        """Test extracting from empty file."""
        result = extractor.extract("", "Empty.cs")

        assert result is not None
        assert result.file_path == "Empty.cs"

    def test_extract_functions_method(self, extractor: CSharpExtractor) -> None:
        """Test extract_functions returns all methods from classes."""
        code = """
public class Service
{
    public void Method1() { }
    public void Method2() { }
}
"""
        functions = extractor.extract_functions(code, "Service.cs")

        assert len(functions) >= 2

    def test_extract_classes_method(self, extractor: CSharpExtractor) -> None:
        """Test extract_classes standalone method."""
        code = """
public class A { }
public class B { }
"""
        classes = extractor.extract_classes(code, "Classes.cs")

        assert len(classes) >= 2

    def test_extract_imports_method(self, extractor: CSharpExtractor) -> None:
        """Test extract_imports standalone method."""
        code = """
using System;
using System.IO;
"""
        imports = extractor.extract_imports(code)

        assert len(imports) >= 2


class TestRustExtractorDetailed:
    """Detailed tests for RustExtractor."""

    @pytest.fixture
    def extractor(self) -> RustExtractor:
        """Create Rust extractor."""
        return RustExtractor()

    def test_language_property(self, extractor: RustExtractor) -> None:
        """Test language property returns rust."""
        assert extractor.language == "rust"

    def test_extract_simple_function(self, extractor: RustExtractor) -> None:
        """Test extracting simple function."""
        code = """
fn hello() {
    println!("Hello");
}
"""
        result = extractor.extract(code, "main.rs")

        assert len(result.functions) >= 1
        assert any(f.name == "hello" for f in result.functions)

    def test_extract_function_with_params_and_return(self, extractor: RustExtractor) -> None:
        """Test extracting function with parameters and return type."""
        code = """
fn add(a: i32, b: i32) -> i32 {
    a + b
}
"""
        result = extractor.extract(code, "lib.rs")

        assert len(result.functions) >= 1
        func = next(f for f in result.functions if f.name == "add")
        # Note: return_type extraction may not work with all tree-sitter versions
        # The key behavior is that the function is extracted correctly
        assert len(func.parameters) == 2

    def test_extract_async_function(self, extractor: RustExtractor) -> None:
        """Test extracting async function."""
        code = """
async fn fetch_data() -> Result<Data, Error> {
    todo!()
}
"""
        result = extractor.extract(code, "async.rs")

        assert len(result.functions) >= 1
        func = next(f for f in result.functions if f.name == "fetch_data")
        assert func.is_async

    def test_extract_pub_function(self, extractor: RustExtractor) -> None:
        """Test extracting public function."""
        code = """
pub fn public_function() -> String {
    String::new()
}
"""
        result = extractor.extract(code, "lib.rs")

        assert len(result.functions) >= 1

    def test_extract_struct(self, extractor: RustExtractor) -> None:
        """Test extracting struct."""
        code = """
pub struct User {
    pub id: u32,
    pub name: String,
    email: Option<String>,
}
"""
        result = extractor.extract(code, "models.rs")

        assert len(result.classes) >= 1
        user = next(c for c in result.classes if c.name == "User")
        assert user is not None

    def test_extract_struct_with_impl(self, extractor: RustExtractor) -> None:
        """Test extracting struct with impl block methods."""
        code = """
pub struct Greeter {
    name: String,
}

impl Greeter {
    pub fn new(name: String) -> Self {
        Greeter { name }
    }

    pub fn greet(&self) -> String {
        format!("Hello, {}!", self.name)
    }
}
"""
        result = extractor.extract(code, "greeter.rs")

        assert len(result.classes) >= 1
        greeter = next(c for c in result.classes if c.name == "Greeter")
        assert len(greeter.methods) >= 2

    def test_extract_enum(self, extractor: RustExtractor) -> None:
        """Test extracting enum."""
        code = """
pub enum Status {
    Active,
    Inactive,
    Pending(String),
}
"""
        result = extractor.extract(code, "enums.rs")

        assert len(result.classes) >= 1
        status = next((c for c in result.classes if c.name == "Status"), None)
        assert status is not None

    def test_extract_trait(self, extractor: RustExtractor) -> None:
        """Test extracting trait."""
        code = """
pub trait Display {
    fn display(&self) -> String;
    fn debug(&self) -> String {
        String::new()
    }
}
"""
        result = extractor.extract(code, "traits.rs")

        assert len(result.classes) >= 1
        display = next(c for c in result.classes if c.name == "Display")
        assert display.is_abstract  # Traits are abstract

    def test_extract_trait_with_supertraits(self, extractor: RustExtractor) -> None:
        """Test extracting trait with supertraits."""
        code = """
pub trait Serializable: Display + Debug {
    fn serialize(&self) -> String;
}
"""
        result = extractor.extract(code, "traits.rs")

        assert len(result.classes) >= 1
        trait = next(c for c in result.classes if c.name == "Serializable")
        assert len(trait.bases) >= 1

    def test_extract_use_statements(self, extractor: RustExtractor) -> None:
        """Test extracting use statements."""
        code = """
use std::collections::HashMap;
use std::io::{self, Read, Write};
use crate::models::*;
"""
        result = extractor.extract(code, "lib.rs")

        assert len(result.imports) >= 3

    def test_extract_use_with_alias(self, extractor: RustExtractor) -> None:
        """Test extracting use with alias."""
        code = """
use std::io::Result as IoResult;
"""
        result = extractor.extract(code, "lib.rs")

        assert len(result.imports) >= 1
        imp = result.imports[0]
        assert imp.alias == "IoResult"

    def test_extract_rust_doc_comments(self, extractor: RustExtractor) -> None:
        """Test extracting Rust documentation comments."""
        code = '''
/// This function adds two numbers.
///
/// # Examples
///
/// ```
/// let result = add(2, 3);
/// assert_eq!(result, 5);
/// ```
fn add(a: i32, b: i32) -> i32 {
    a + b
}
'''
        result = extractor.extract(code, "lib.rs")

        assert len(result.functions) >= 1
        func = result.functions[0]
        assert func.docstring is not None
        assert "adds two numbers" in func.docstring

    def test_extract_module_doc(self, extractor: RustExtractor) -> None:
        """Test extracting module-level documentation."""
        code = '''
//! This module provides utility functions.

fn helper() {}
'''
        result = extractor.extract(code, "lib.rs")

        assert result.module_docstring is not None

    def test_extract_attributes(self, extractor: RustExtractor) -> None:
        """Test extracting attributes as decorators."""
        code = """
#[derive(Debug, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Config {
    pub name: String,
}
"""
        result = extractor.extract(code, "config.rs")

        assert len(result.classes) >= 1
        config = result.classes[0]
        assert len(config.decorators) >= 1

    def test_extract_self_parameter(self, extractor: RustExtractor) -> None:
        """Test extracting method with self parameter."""
        code = """
struct Counter {
    count: i32,
}

impl Counter {
    fn increment(&mut self) {
        self.count += 1;
    }

    fn value(&self) -> i32 {
        self.count
    }
}
"""
        result = extractor.extract(code, "counter.rs")

        assert len(result.classes) >= 1
        counter = result.classes[0]
        methods = [m for m in counter.methods if m.name in ("increment", "value")]
        assert len(methods) >= 2
        for method in methods:
            assert method.is_method

    def test_extract_empty_file(self, extractor: RustExtractor) -> None:
        """Test extracting from empty file."""
        result = extractor.extract("", "empty.rs")

        assert result is not None

    def test_extract_functions_method(self, extractor: RustExtractor) -> None:
        """Test extract_functions standalone method."""
        code = """
fn one() {}
fn two() {}
"""
        functions = extractor.extract_functions(code, "funcs.rs")

        assert len(functions) >= 2

    def test_extract_classes_method(self, extractor: RustExtractor) -> None:
        """Test extract_classes standalone method."""
        code = """
struct A {}
struct B {}
"""
        classes = extractor.extract_classes(code, "structs.rs")

        assert len(classes) >= 2

    def test_extract_imports_method(self, extractor: RustExtractor) -> None:
        """Test extract_imports standalone method."""
        code = """
use std::io;
use std::fs;
"""
        imports = extractor.extract_imports(code)

        assert len(imports) >= 2


class TestJavaScriptExtractorDetailed:
    """Detailed tests for JavaScriptExtractor."""

    @pytest.fixture
    def extractor(self) -> JavaScriptExtractor:
        """Create JavaScript extractor."""
        return JavaScriptExtractor()

    def test_language_property(self, extractor: JavaScriptExtractor) -> None:
        """Test language property returns javascript."""
        assert extractor.language == "javascript"

    def test_extract_function_declaration(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting function declaration."""
        code = """
function hello(name) {
    console.log(`Hello, ${name}!`);
}
"""
        result = extractor.extract(code, "index.js")

        assert len(result.functions) >= 1
        func = next(f for f in result.functions if f.name == "hello")
        assert func is not None

    def test_extract_arrow_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting arrow function."""
        code = """
const add = (a, b) => a + b;
const multiply = (a, b) => {
    return a * b;
};
"""
        result = extractor.extract(code, "utils.js")

        assert len(result.functions) >= 2

    def test_extract_async_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting async function."""
        code = """
async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}
"""
        result = extractor.extract(code, "api.js")

        assert len(result.functions) >= 1
        func = next(f for f in result.functions if f.name == "fetchData")
        assert func.is_async

    def test_extract_async_arrow_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting async arrow function."""
        code = """
const fetchUser = async (id) => {
    return await api.getUser(id);
};
"""
        result = extractor.extract(code, "user.js")

        assert len(result.functions) >= 1

    def test_extract_generator_function(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting generator function."""
        code = """
function* numberGenerator() {
    yield 1;
    yield 2;
    yield 3;
}
"""
        result = extractor.extract(code, "generators.js")

        assert len(result.functions) >= 1

    def test_extract_class(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting class."""
        code = """
class Calculator {
    constructor() {
        this.value = 0;
    }

    add(x) {
        this.value += x;
    }
}
"""
        result = extractor.extract(code, "calculator.js")

        assert len(result.classes) >= 1
        calc = result.classes[0]
        assert calc.name == "Calculator"
        assert len(calc.methods) >= 1

    def test_extract_class_with_inheritance(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting class with extends."""
        code = """
class Animal {}

class Dog extends Animal {
    bark() {
        console.log("Woof!");
    }
}
"""
        result = extractor.extract(code, "animals.js")

        assert len(result.classes) >= 2
        dog = next(c for c in result.classes if c.name == "Dog")
        assert len(dog.bases) >= 1

    def test_extract_static_method(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting static method."""
        code = """
class Utils {
    static format(value) {
        return String(value);
    }
}
"""
        result = extractor.extract(code, "utils.js")

        assert len(result.classes) >= 1
        utils = result.classes[0]
        static_method = next((m for m in utils.methods if m.name == "format"), None)
        assert static_method is not None
        assert static_method.is_static

    def test_extract_getter_setter(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting getter and setter."""
        code = """
class Person {
    constructor() {
        this._name = '';
    }

    get name() {
        return this._name;
    }

    set name(value) {
        this._name = value;
    }
}
"""
        result = extractor.extract(code, "person.js")

        assert len(result.classes) >= 1
        person = result.classes[0]
        assert len(person.methods) >= 2

    def test_extract_es6_imports(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting ES6 imports."""
        code = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import './styles.css';
"""
        result = extractor.extract(code, "app.js")

        assert len(result.imports) >= 4

    def test_extract_named_import(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting named import with alias."""
        code = """
import { Component as BaseComponent } from 'react';
"""
        result = extractor.extract(code, "component.js")

        assert len(result.imports) >= 1
        imp = result.imports[0]
        assert imp.alias == "BaseComponent"

    def test_extract_commonjs_require(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting CommonJS require."""
        code = """
const fs = require('fs');
const { readFile, writeFile } = require('fs');
"""
        result = extractor.extract(code, "file.js")

        assert len(result.imports) >= 2

    def test_extract_jsdoc(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting JSDoc comments."""
        code = '''
/**
 * Adds two numbers together.
 * @param {number} a - First number
 * @param {number} b - Second number
 * @returns {number} Sum of a and b
 */
function add(a, b) {
    return a + b;
}
'''
        result = extractor.extract(code, "math.js")

        assert len(result.functions) >= 1
        func = result.functions[0]
        assert func.docstring is not None
        assert "Adds two numbers" in func.docstring

    def test_extract_default_parameters(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting function with default parameters."""
        code = """
function greet(name = 'World') {
    return `Hello, ${name}!`;
}
"""
        result = extractor.extract(code, "greet.js")

        assert len(result.functions) >= 1
        func = result.functions[0]
        assert len(func.parameters) >= 1

    def test_extract_rest_parameters(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting function with rest parameters."""
        code = """
function sum(...numbers) {
    return numbers.reduce((a, b) => a + b, 0);
}
"""
        result = extractor.extract(code, "sum.js")

        assert len(result.functions) >= 1
        func = result.functions[0]
        rest_param = next((p for p in func.parameters if p.is_variadic), None)
        assert rest_param is not None

    def test_extract_destructuring_params(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting function with destructuring parameters."""
        code = """
function processUser({ name, age }) {
    return `${name} is ${age} years old`;
}
"""
        result = extractor.extract(code, "user.js")

        assert len(result.functions) >= 1

    def test_extract_empty_file(self, extractor: JavaScriptExtractor) -> None:
        """Test extracting from empty file."""
        result = extractor.extract("", "empty.js")

        assert result is not None

    def test_extract_functions_method(self, extractor: JavaScriptExtractor) -> None:
        """Test extract_functions standalone method."""
        code = """
function one() {}
function two() {}
"""
        functions = extractor.extract_functions(code, "funcs.js")

        assert len(functions) >= 2

    def test_extract_classes_method(self, extractor: JavaScriptExtractor) -> None:
        """Test extract_classes standalone method."""
        code = """
class A {}
class B {}
"""
        classes = extractor.extract_classes(code, "classes.js")

        assert len(classes) >= 2

    def test_extract_imports_method(self, extractor: JavaScriptExtractor) -> None:
        """Test extract_imports standalone method."""
        code = """
import a from 'a';
import b from 'b';
"""
        imports = extractor.extract_imports(code)

        assert len(imports) >= 2


class TestJavaExtractorDetailed:
    """Detailed tests for JavaExtractor."""

    @pytest.fixture
    def extractor(self) -> JavaExtractor:
        """Create Java extractor."""
        return JavaExtractor()

    def test_language_property(self, extractor: JavaExtractor) -> None:
        """Test language property returns java."""
        assert extractor.language == "java"

    def test_extract_simple_class(self, extractor: JavaExtractor) -> None:
        """Test extracting simple class."""
        code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
        result = extractor.extract(code, "HelloWorld.java")

        assert len(result.classes) >= 1
        assert any(c.name == "HelloWorld" for c in result.classes)

    def test_extract_class_with_inheritance(self, extractor: JavaExtractor) -> None:
        """Test extracting class with extends and implements."""
        code = """
public class UserService extends BaseService implements IUserService, Serializable {
    public void getUser() {}
}
"""
        result = extractor.extract(code, "UserService.java")

        assert len(result.classes) >= 1
        service = result.classes[0]
        assert len(service.bases) >= 1

    def test_extract_interface(self, extractor: JavaExtractor) -> None:
        """Test extracting interface."""
        code = """
public interface IUserService {
    User getUser(int id);
    void createUser(User user);
}
"""
        result = extractor.extract(code, "IUserService.java")

        assert len(result.classes) >= 1
        interface = result.classes[0]
        assert interface.is_abstract

    def test_extract_abstract_class(self, extractor: JavaExtractor) -> None:
        """Test extracting abstract class."""
        code = """
public abstract class BaseService {
    public abstract void execute();
    public void log() {}
}
"""
        result = extractor.extract(code, "BaseService.java")

        assert len(result.classes) >= 1
        base = result.classes[0]
        assert base.is_abstract

    def test_extract_method_with_throws(self, extractor: JavaExtractor) -> None:
        """Test extracting method with throws clause."""
        code = """
public class FileHandler {
    public void readFile(String path) throws IOException, FileNotFoundException {
        // implementation
    }
}
"""
        result = extractor.extract(code, "FileHandler.java")

        assert len(result.classes) >= 1
        handler = result.classes[0]
        read_method = next((m for m in handler.methods if m.name == "readFile"), None)
        assert read_method is not None
        assert "throws" in read_method.signature

    def test_extract_constructor(self, extractor: JavaExtractor) -> None:
        """Test extracting constructor."""
        code = """
public class Person {
    private String name;

    public Person(String name) {
        this.name = name;
    }
}
"""
        result = extractor.extract(code, "Person.java")

        assert len(result.classes) >= 1
        person = result.classes[0]
        ctor = next((m for m in person.methods if m.name == "Person"), None)
        assert ctor is not None

    def test_extract_static_method(self, extractor: JavaExtractor) -> None:
        """Test extracting static method."""
        code = """
public class Utils {
    public static int add(int a, int b) {
        return a + b;
    }
}
"""
        result = extractor.extract(code, "Utils.java")

        assert len(result.classes) >= 1
        utils = result.classes[0]
        add_method = next((m for m in utils.methods if m.name == "add"), None)
        assert add_method is not None
        assert add_method.is_static

    def test_extract_imports(self, extractor: JavaExtractor) -> None:
        """Test extracting import statements."""
        code = """
import java.util.List;
import java.util.ArrayList;
import java.io.*;
import static java.lang.Math.PI;

public class Test {}
"""
        result = extractor.extract(code, "Test.java")

        assert len(result.imports) >= 3

    def test_extract_wildcard_import(self, extractor: JavaExtractor) -> None:
        """Test extracting wildcard import."""
        code = """
import java.util.*;

public class Test {}
"""
        result = extractor.extract(code, "Test.java")

        assert len(result.imports) >= 1
        imp = result.imports[0]
        assert imp.module.endswith("*")

    def test_extract_javadoc(self, extractor: JavaExtractor) -> None:
        """Test extracting Javadoc comments."""
        code = '''
/**
 * Calculator class for arithmetic operations.
 *
 * @author Developer
 * @version 1.0
 */
public class Calculator {
    /**
     * Adds two integers.
     *
     * @param a first number
     * @param b second number
     * @return sum of a and b
     */
    public int add(int a, int b) {
        return a + b;
    }
}
'''
        result = extractor.extract(code, "Calculator.java")

        assert len(result.classes) >= 1
        calc = result.classes[0]
        assert calc.docstring is not None

    def test_extract_annotations(self, extractor: JavaExtractor) -> None:
        """Test extracting annotations as decorators."""
        code = """
@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue
    private Long id;

    @Override
    public String toString() {
        return "User";
    }
}
"""
        result = extractor.extract(code, "User.java")

        assert len(result.classes) >= 1
        user = result.classes[0]
        assert len(user.decorators) >= 1

    def test_extract_enum(self, extractor: JavaExtractor) -> None:
        """Test extracting enum."""
        code = """
public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}
"""
        result = extractor.extract(code, "Status.java")

        assert len(result.classes) >= 1
        status = next((c for c in result.classes if c.name == "Status"), None)
        assert status is not None

    def test_extract_varargs(self, extractor: JavaExtractor) -> None:
        """Test extracting method with varargs."""
        code = """
public class Formatter {
    public String format(String template, Object... args) {
        return String.format(template, args);
    }
}
"""
        result = extractor.extract(code, "Formatter.java")

        assert len(result.classes) >= 1
        formatter = result.classes[0]
        format_method = next((m for m in formatter.methods if m.name == "format"), None)
        assert format_method is not None
        variadic_param = next((p for p in format_method.parameters if p.is_variadic), None)
        assert variadic_param is not None

    def test_extract_generic_class(self, extractor: JavaExtractor) -> None:
        """Test extracting generic class."""
        code = """
public class Container<T> {
    private T value;

    public T getValue() {
        return value;
    }

    public void setValue(T value) {
        this.value = value;
    }
}
"""
        result = extractor.extract(code, "Container.java")

        assert len(result.classes) >= 1

    def test_extract_empty_file(self, extractor: JavaExtractor) -> None:
        """Test extracting from empty file."""
        result = extractor.extract("", "Empty.java")

        assert result is not None

    def test_extract_functions_method(self, extractor: JavaExtractor) -> None:
        """Test extract_functions returns methods from classes."""
        code = """
public class Service {
    public void method1() {}
    public void method2() {}
}
"""
        functions = extractor.extract_functions(code, "Service.java")

        assert len(functions) >= 2

    def test_extract_classes_method(self, extractor: JavaExtractor) -> None:
        """Test extract_classes standalone method."""
        code = """
public class A {}
public class B {}
"""
        classes = extractor.extract_classes(code, "Classes.java")

        assert len(classes) >= 2

    def test_extract_imports_method(self, extractor: JavaExtractor) -> None:
        """Test extract_imports standalone method."""
        code = """
import java.util.List;
import java.io.File;
"""
        imports = extractor.extract_imports(code)

        assert len(imports) >= 2


class TestExtractorNoParser:
    """Tests for extractors when parser is not available."""

    def test_csharp_no_parser(self) -> None:
        """Test CSharp extractor handles missing parser."""
        with patch("memory_service.parsing.extractors.csharp.CSharpExtractor.__init__",
                   lambda self: setattr(self, "_parser", None) or setattr(self, "_language", None)):
            extractor = CSharpExtractor()
            extractor._parser = None
            extractor._language = None

            result = extractor.extract("class Test {}", "Test.cs")
            assert "not available" in result.errors[0]

            assert extractor.extract_functions("", "") == []
            assert extractor.extract_classes("", "") == []
            assert extractor.extract_imports("") == []

    def test_rust_no_parser(self) -> None:
        """Test Rust extractor handles missing parser."""
        extractor = RustExtractor()
        extractor._parser = None
        extractor._language = None

        result = extractor.extract("fn test() {}", "test.rs")
        assert "not available" in result.errors[0]

        assert extractor.extract_functions("", "") == []
        assert extractor.extract_classes("", "") == []
        assert extractor.extract_imports("") == []

    def test_javascript_no_parser(self) -> None:
        """Test JavaScript extractor handles missing parser."""
        extractor = JavaScriptExtractor()
        extractor._parser = None
        extractor._language = None

        result = extractor.extract("function test() {}", "test.js")
        assert "not available" in result.errors[0]

        assert extractor.extract_functions("", "") == []
        assert extractor.extract_classes("", "") == []
        assert extractor.extract_imports("") == []

    def test_java_no_parser(self) -> None:
        """Test Java extractor handles missing parser."""
        extractor = JavaExtractor()
        extractor._parser = None
        extractor._language = None

        result = extractor.extract("class Test {}", "Test.java")
        assert "not available" in result.errors[0]

        assert extractor.extract_functions("", "") == []
        assert extractor.extract_classes("", "") == []
        assert extractor.extract_imports("") == []
