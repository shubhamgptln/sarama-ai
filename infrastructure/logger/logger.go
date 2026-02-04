package logger

import (
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// Level represents the logging level
type Level int

const (
	DebugLevel Level = iota
	InfoLevel
	WarnLevel
	ErrorLevel
	FatalLevel
)

var levelNames = map[Level]string{
	DebugLevel: "DEBUG",
	InfoLevel:  "INFO",
	WarnLevel:  "WARN",
	ErrorLevel: "ERROR",
	FatalLevel: "FATAL",
}

// Logger is the main logger interface
type Logger interface {
	Debug(msg string, fields ...Field)
	Info(msg string, fields ...Field)
	Warn(msg string, fields ...Field)
	Error(msg string, fields ...Field)
	Fatal(msg string, fields ...Field)
	WithField(key string, value interface{}) Logger
	WithFields(fields ...Field) Logger
}

// Field represents a structured log field
type Field struct {
	Key   string
	Value interface{}
}

// zapLogger is the concrete implementation
type zapLogger struct {
	level      Level
	output     io.Writer
	mu         sync.Mutex
	fields     []Field
	caller     bool
	callerSkip int
}

// New creates a new logger instance
func New(level Level) Logger {
	return &zapLogger{
		level:      level,
		output:     os.Stdout,
		fields:     make([]Field, 0),
		caller:     true,
		callerSkip: 2,
	}
}

// NewWithWriter creates a new logger with custom output
func NewWithWriter(level Level, output io.Writer) Logger {
	return &zapLogger{
		level:      level,
		output:     output,
		fields:     make([]Field, 0),
		caller:     true,
		callerSkip: 2,
	}
}

// Debug logs a debug message
func (l *zapLogger) Debug(msg string, fields ...Field) {
	if l.level <= DebugLevel {
		l.log(DebugLevel, msg, fields...)
	}
}

// Info logs an info message
func (l *zapLogger) Info(msg string, fields ...Field) {
	if l.level <= InfoLevel {
		l.log(InfoLevel, msg, fields...)
	}
}

// Warn logs a warning message
func (l *zapLogger) Warn(msg string, fields ...Field) {
	if l.level <= WarnLevel {
		l.log(WarnLevel, msg, fields...)
	}
}

// Error logs an error message
func (l *zapLogger) Error(msg string, fields ...Field) {
	if l.level <= ErrorLevel {
		l.log(ErrorLevel, msg, fields...)
	}
}

// Fatal logs a fatal message and exits
func (l *zapLogger) Fatal(msg string, fields ...Field) {
	l.log(FatalLevel, msg, fields...)
	os.Exit(1)
}

// WithField adds a single field to the logger
func (l *zapLogger) WithField(key string, value interface{}) Logger {
	newLogger := &zapLogger{
		level:      l.level,
		output:     l.output,
		fields:     append(l.fields, Field{Key: key, Value: value}),
		caller:     l.caller,
		callerSkip: l.callerSkip,
	}
	return newLogger
}

// WithFields adds multiple fields to the logger
func (l *zapLogger) WithFields(fields ...Field) Logger {
	newFields := append(l.fields, fields...)
	newLogger := &zapLogger{
		level:      l.level,
		output:     l.output,
		fields:     newFields,
		caller:     l.caller,
		callerSkip: l.callerSkip,
	}
	return newLogger
}

// log performs the actual logging
func (l *zapLogger) log(level Level, msg string, fields ...Field) {
	l.mu.Lock()
	defer l.mu.Unlock()

	// Combine logger fields and call fields
	allFields := append(l.fields, fields...)

	// Get caller info
	caller := ""
	if l.caller {
		if pc, file, line, ok := runtime.Caller(l.callerSkip); ok {
			funcName := runtime.FuncForPC(pc).Name()
			// Extract short function name
			if idx := strings.LastIndexByte(funcName, '.'); idx >= 0 {
				funcName = funcName[idx+1:]
			}
			// Extract short file name
			file = filepath.Base(file)
			caller = fmt.Sprintf("%s:%d (%s)", file, line, funcName)
		}
	}

	// Format log message
	timestamp := time.Now().Format("2006-01-02T15:04:05.000Z07:00")
	levelStr := levelNames[level]

	// Build fields string
	fieldsStr := ""
	if len(allFields) > 0 {
		fieldsStr = " "
		for i, f := range allFields {
			if i > 0 {
				fieldsStr += " "
			}
			fieldsStr += fmt.Sprintf("%s=%v", f.Key, f.Value)
		}
	}

	// Add caller info
	if caller != "" {
		fieldsStr += fmt.Sprintf(" caller=%s", caller)
	}

	// Format: timestamp [LEVEL] message fields...
	logLine := fmt.Sprintf("%s [%s] %s%s\n", timestamp, levelStr, msg, fieldsStr)

	// Write to output
	if _, err := io.WriteString(l.output, logLine); err != nil {
		// Fallback to std logger if write fails
		log.Print(logLine)
	}
}

// Global logger instance
var globalLogger Logger = New(InfoLevel)

// SetGlobalLogger sets the global logger instance
func SetGlobalLogger(logger Logger) {
	globalLogger = logger
}

// GetGlobalLogger returns the global logger instance
func GetGlobalLogger() Logger {
	return globalLogger
}

// Convenience functions using global logger
func Debug(msg string, fields ...Field) {
	globalLogger.Debug(msg, fields...)
}

func Info(msg string, fields ...Field) {
	globalLogger.Info(msg, fields...)
}

func Warn(msg string, fields ...Field) {
	globalLogger.Warn(msg, fields...)
}

func Error(msg string, fields ...Field) {
	globalLogger.Error(msg, fields...)
}

func Fatal(msg string, fields ...Field) {
	globalLogger.Fatal(msg, fields...)
}

func WithField(key string, value interface{}) Logger {
	return globalLogger.WithField(key, value)
}

func WithFields(fields ...Field) Logger {
	return globalLogger.WithFields(fields...)
}
