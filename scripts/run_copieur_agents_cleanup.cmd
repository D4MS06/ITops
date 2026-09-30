@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "ENV_FILE=%~1"
set "APPLY=%~2"
if "%ENV_FILE%"=="" set "ENV_FILE=%~dp0local_dev_env.cmd"
if not exist "%ENV_FILE%" (
  echo Fichier d'environnement introuvable : %ENV_FILE%
  exit /b 1
)

call "%ENV_FILE%"
if not defined NMP_MARIADB_HOST goto :missing_variables
if not defined NMP_MARIADB_PORT goto :missing_variables
if not defined NMP_MARIADB_USER goto :missing_variables
if not defined NMP_MARIADB_PASSWORD goto :missing_variables
if not defined NMP_MARIADB_DATABASE goto :missing_variables

set "MARIADB_CLIENT=%NMP_MARIADB_BIN_DIR%\mariadb.exe"
if not exist "%MARIADB_CLIENT%" set "MARIADB_CLIENT=%NMP_MARIADB_BIN_DIR%\mysql.exe"
if not exist "%MARIADB_CLIENT%" (
  echo Client MariaDB introuvable. Definissez NMP_MARIADB_BIN_DIR dans le fichier d'environnement.
  exit /b 1
)

set "MYSQL_PWD=%NMP_MARIADB_PASSWORD%"
set "MARIADB_ARGS=--host=%NMP_MARIADB_HOST% --port=%NMP_MARIADB_PORT% --user=%NMP_MARIADB_USER% --database=%NMP_MARIADB_DATABASE% --default-character-set=utf8mb4 --batch --raw"

echo Cible MariaDB : %NMP_MARIADB_HOST%:%NMP_MARIADB_PORT% / %NMP_MARIADB_DATABASE%
echo Relations historiques detectees :
"%MARIADB_CLIENT%" %MARIADB_ARGS% -e "SELECT r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active, COUNT(l.id) AS link_count FROM custom_service_relations r LEFT JOIN custom_service_relation_links l ON l.relation_id = r.id WHERE r.target_service_code = 'utilisateurs' AND r.source_service_code IN ('copieur', 'code_copieur') AND r.display_label = 'Agents' GROUP BY r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active ORDER BY r.id;"
if errorlevel 1 goto :failed

if /I not "%APPLY%"=="-Apply" (
  echo.
  echo Aucune modification appliquee. La migration est desormais non destructive ; -Apply execute seulement le rapport complet.
  exit /b 0
)

echo Execution du rapport de verification...
"%MARIADB_CLIENT%" %MARIADB_ARGS% < "%~dp0..\deployment\sql\20260930_supprimer_relations_agents_copieurs.sql"
if errorlevel 1 goto :failed
echo Rapport termine : aucune relation ni aucun lien n'a ete supprime.
exit /b 0

:missing_variables
echo Variables MariaDB absentes du fichier d'environnement.
exit /b 1

:failed
echo L'operation a echoue. Aucune correction manuelle n'a ete appliquee.
exit /b 1
