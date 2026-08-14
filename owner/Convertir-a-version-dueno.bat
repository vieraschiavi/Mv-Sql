@echo off
rem (c) 2026 Martin Viera. Todos los derechos reservados.
rem Punto de entrada. No lleva nada sensible adentro -- solo invoca el
rem .ps1 que esta al lado. Ver owner/README.md.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0convertir-a-version-dueno.ps1"
