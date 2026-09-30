-- Nettoyage de production : Copieurs et Personnel scolaire.
--
-- Cette migration retire uniquement les anciennes relations vers le
-- referentiel systeme Agents. Les relations vers Personnel scolaire et Ecoles
-- restent intactes. Executer apres une sauvegarde complete ITops.
--
-- Le script est idempotent : s'il a deja ete applique, il ne supprime rien.

START TRANSACTION;

CREATE TEMPORARY TABLE itops_legacy_copieur_agent_relations (
    id BIGINT NOT NULL PRIMARY KEY
);

INSERT INTO itops_legacy_copieur_agent_relations (id)
SELECT id
FROM custom_service_relations
WHERE target_service_code = 'utilisateurs'
  AND source_service_code IN ('copieur', 'code_copieur')
  AND display_label = 'Agents';

-- Les relations scolaires doivent exister avant de retirer les relations
-- historiques. Cette garde evite de rendre les attributions inaccessibles.
SET @school_relation_count := (
    SELECT COUNT(*)
    FROM custom_service_relations
    WHERE (source_service_code = 'copieur' AND target_service_code = 'personnel_scolaire')
       OR (source_service_code = 'code_copieur' AND target_service_code = 'personnel_scolaire')
);
SET @preflight_sql := CASE
    WHEN @school_relation_count < 2
        THEN 'SELECT * FROM __itops_abort_missing_personnel_scolaire_relations__'
    ELSE 'SELECT ''Precontrole Copieurs : relations scolaires presentes'' AS message'
END;
PREPARE itops_preflight_statement FROM @preflight_sql;
EXECUTE itops_preflight_statement;
DEALLOCATE PREPARE itops_preflight_statement;

-- Conserver ces compteurs dans la sortie d'execution pour le compte rendu.
SELECT
    (SELECT COUNT(*) FROM itops_legacy_copieur_agent_relations) AS relations_agents_a_supprimer,
    (SELECT COUNT(*) FROM custom_service_relation_links l
        JOIN itops_legacy_copieur_agent_relations r ON r.id = l.relation_id) AS liens_agents_a_supprimer;

-- Les liens sont des attributions obsoletes provenant de l'AD principal.
-- Les relations Code copieur -> Personnel scolaire restent la source des
-- attributions scolaires et ne sont jamais visees ici.
DELETE l
FROM custom_service_relation_links l
JOIN itops_legacy_copieur_agent_relations r ON r.id = l.relation_id;

DELETE r
FROM custom_service_relations r
JOIN itops_legacy_copieur_agent_relations legacy ON legacy.id = r.id;

SELECT
    (SELECT COUNT(*) FROM custom_service_relations
        WHERE target_service_code = 'utilisateurs'
          AND source_service_code IN ('copieur', 'code_copieur')
          AND display_label = 'Agents') AS relations_agents_restantes,
    (SELECT COUNT(*) FROM custom_service_relations
        WHERE source_service_code = 'code_copieur'
          AND target_service_code = 'personnel_scolaire') AS relations_personnel_scolaire_restantes;

COMMIT;
