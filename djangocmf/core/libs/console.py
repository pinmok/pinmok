#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Console Output Manager

Description:
  A unified console output manager that supports multiple environments
  (CLI, Django commands, JSON output) with a consistent API.
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-11-08
"""
import sys
from enum import Enum

from django.core.management import BaseCommand


class MessageLevel(Enum):
    """Standard message levels for consistent logging across the application."""
    LOG = 'log'
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    DEBUG = 'debug'
    STEP = 'step'
    STEP_DONE = 'step_done'
    STEP_FAIL = 'step_fail'


class Console:
    """
    Universal console output manager with environment-aware routing.

    Provides a unified API for outputting messages in both CLI and 
    Django management command environments.

    Usage:
        # CLI usage
        console = Console()
        console.info("Processing started")
        console.success("Task completed", items_processed=42)

        # Django command usage  
        console = Console(django_command=self)
        console.step("Processing domain", domain="django")
    """

    # ANSI color codes for terminal output
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"

    # Mapping of message levels to ANSI colors for CLI output
    LEVEL_COLORS = {
        MessageLevel.LOG: WHITE,
        MessageLevel.INFO: CYAN,
        MessageLevel.SUCCESS: GREEN,
        MessageLevel.WARNING: YELLOW,
        MessageLevel.ERROR: RED,
        MessageLevel.DEBUG: BLUE,
        MessageLevel.STEP: CYAN,
        MessageLevel.STEP_DONE: GREEN,
        MessageLevel.STEP_FAIL: RED,
    }

    def __init__(self, django_command: BaseCommand | None = None, verbose: bool = False):
        """
        Initialize the console output manager.

        Args:
            django_command: Django management command instance for Django-aware output
            verbose: Whether to include metadata in human-readable output
        """
        self._verbose: bool = verbose
        self._django_command: BaseCommand = django_command

    def log(self, message: str, **kwargs):
        self.output(MessageLevel.LOG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self.output(MessageLevel.INFO, message, **kwargs)

    def success(self, message: str, **kwargs):
        self.output(MessageLevel.SUCCESS, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.output(MessageLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self.output(MessageLevel.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.output(MessageLevel.DEBUG, message, **kwargs)

    def step(self, message: str, **kwargs):
        self.output(MessageLevel.STEP, message, **kwargs)

    def step_done(self, message: str, **kwargs):
        self.output(MessageLevel.STEP_DONE, message, **kwargs)

    def step_fail(self, message: str, **kwargs):
        self.output(MessageLevel.STEP_FAIL, message, **kwargs)

    def output(self, level: MessageLevel, message: str, **metadata) -> None:
        """
        Unified output routing based on configured environment.
        """
        if self._django_command:
            self._django_output(level, message, **metadata)
        else:
            self._cli_output(level, message, **metadata)

    def _cli_output(self, level: MessageLevel, message: str, **metadata) -> None:
        """
        Output message for command-line interface environment.
        """
        label = level.name
        color = self.LEVEL_COLORS.get(level, self.WHITE)

        # Format the message with optional metadata
        if metadata and self._verbose:
            details = " ".join(f"{k}={v}" for k, v in metadata.items())
            output_message = f"{message} ({details})"
        else:
            output_message = message

        # Apply color formatting only if output is a terminal
        if sys.stdout.isatty():
            formatted_output = f"{color}[{label}]{self.RESET} {output_message}"
        else:
            formatted_output = f"[{label}] {output_message}"

        print(formatted_output)

    def _django_output(self, level: MessageLevel, message: str, **metadata) -> None:
        """
        Output message for Django management command environment.
        """
        if not self._django_command:
            return

        # Format the message with optional metadata
        if metadata and self._verbose:
            details = " ".join(f"{k}={v}" for k, v in metadata.items())
            output_message = f"{message} ({details})"
        else:
            output_message = message

        style_message = ""
        match level:
            case MessageLevel.SUCCESS | MessageLevel.STEP_DONE:
                style_message = self._django_command.style.SUCCESS(output_message)
            case MessageLevel.WARNING:
                style_message = self._django_command.style.WARNING(output_message)
            case MessageLevel.ERROR | MessageLevel.STEP_FAIL:
                style_message = self._django_command.style.ERROR(output_message)
            case _:
                style_message = self._django_command.style.NOTICE(output_message)

        self._django_command.stdout.write(style_message)
