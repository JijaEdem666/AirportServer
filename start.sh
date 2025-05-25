#!/usr/bin/env bash
# Делает сервер доступным на любом интерфейсе, порт берётся из переменных Render
uvicorn main:host.app --host 0.0.0.0 --port ${PORT:-10000}