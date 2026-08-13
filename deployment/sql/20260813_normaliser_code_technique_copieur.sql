-- Migration de normalisation du module « Copieur ».
--
-- Objectif : remplacer le code technique historique `imprimante` par `copieur`
-- afin de l'aligner avec les relations Ecoles / Personnel scolaire et la base
-- locale. Les identifiants de fiches et les lignes de liens restent inchangés.
--
-- Pré-requis : MariaDB 10.11+ et une sauvegarde récente de la base.
-- Le script est idempotent. Il s'arrête avant toute modification si les deux
-- modules techniques `imprimante` et `copieur` existent simultanément : cette
-- situation nécessiterait une fusion explicite, à ne jamais faire à l'aveugle.

SET @legacy_code := 'imprimante';
SET @canonical_code := 'copieur';

SET @has_legacy := (
    SELECT COUNT(*) FROM custom_services WHERE code = @legacy_code
);
SET @has_canonical := (
    SELECT COUNT(*) FROM custom_services WHERE code = @canonical_code
);

-- Garde-fou exécuté avant l'ouverture de la transaction.
SET @preflight_sql := CASE
    WHEN @has_legacy > 0 AND @has_canonical > 0
        THEN 'SELECT * FROM __itops_abort_copieur_code_conflict__'
    WHEN @has_legacy = 0 AND @has_canonical = 0
        THEN 'SELECT * FROM __itops_abort_copieur_module_missing__'
    ELSE 'SELECT ''Migration Copieur : precontrole valide'' AS message'
END;
PREPARE preflight_statement FROM @preflight_sql;
EXECUTE preflight_statement;
DEALLOCATE PREPARE preflight_statement;

SET @previous_foreign_key_checks := @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;
START TRANSACTION;

-- Conserve les fiches Copieur, leurs champs, leur index de recherche et tout
-- l'historique d'activite (dont les changements de statut).
UPDATE custom_service_fields
SET service_code = @canonical_code
WHERE service_code = @legacy_code;

UPDATE custom_service_records
SET service_code = @canonical_code
WHERE service_code = @legacy_code;

UPDATE custom_service_record_history
SET service_code = @canonical_code
WHERE service_code = @legacy_code;

UPDATE custom_service_record_index
SET service_code = @canonical_code
WHERE service_code = @legacy_code;

-- Met a jour les definitions existantes sans toucher a leurs identifiants ni
-- aux lignes de custom_service_relation_links qui les referencent.
UPDATE custom_service_relations
SET source_service_code = @canonical_code
WHERE source_service_code = @legacy_code;

UPDATE custom_service_relations
SET target_service_code = @canonical_code
WHERE target_service_code = @legacy_code;

UPDATE custom_service_relations
SET assignment_resource_service_code = @canonical_code
WHERE assignment_resource_service_code = @legacy_code;

UPDATE notification_tasks
SET source_service_code = @canonical_code
WHERE source_service_code = @legacy_code;

UPDATE storage_targets
SET service_code = @canonical_code
WHERE service_code = @legacy_code;

-- Les configurations TreeView peuvent contenir le code d'un module lie.
UPDATE custom_services
SET treeview_config = REPLACE(treeview_config, @legacy_code, @canonical_code)
WHERE treeview_config LIKE CONCAT('%', @legacy_code, '%');

-- Renommage final du module parent une fois toutes les references migrees.
UPDATE custom_services
SET code = @canonical_code,
    label = 'Copieur'
WHERE code = @legacy_code;

-- Conserve l'acces au module depuis les menus et les droits existants.
UPDATE auth_modules
SET route_path = REPLACE(route_path, CONCAT('service=', @legacy_code), CONCAT('service=', @canonical_code))
WHERE route_path LIKE CONCAT('%service=', @legacy_code, '%');

-- Alignement de la relation Personnel scolaire -> Ecoles : elle permet de
-- propager les relations Ecole -> Copieur vers les fiches du personnel.
UPDATE custom_service_relations
SET show_indirect_relations = 1,
    is_active = 1
WHERE source_service_code = 'personnel_scolaire'
  AND target_service_code = 'personnel_scolaire_ou'
  AND direction = 'out';

-- Ecole <- Copieur : une ecole peut avoir plusieurs copieurs.
INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction,
    display_label, required, is_active,
    filter_candidates_by_shared_relation, show_indirect_relations,
    record_display_mode, assignment_resource_service_code,
    unique_value_field_key, sort_order
) VALUES (
    'copieur', 'personnel_scolaire_ou', 'est installe dans', 'many_to_one', 'out',
    'Ecole', 0, 1,
    0, 1,
    'standard', '',
    '', 30
)
ON DUPLICATE KEY UPDATE
    verb = VALUES(verb),
    display_label = VALUES(display_label),
    required = VALUES(required),
    is_active = VALUES(is_active),
    filter_candidates_by_shared_relation = VALUES(filter_candidates_by_shared_relation),
    show_indirect_relations = VALUES(show_indirect_relations),
    record_display_mode = VALUES(record_display_mode),
    assignment_resource_service_code = VALUES(assignment_resource_service_code),
    unique_value_field_key = VALUES(unique_value_field_key),
    sort_order = VALUES(sort_order);

-- Attribution Copieur + Code copieur au Personnel scolaire, avec la meme
-- mecanique d'affichage que pour les Agents.
INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction,
    display_label, required, is_active,
    filter_candidates_by_shared_relation, show_indirect_relations,
    record_display_mode, assignment_resource_service_code,
    unique_value_field_key, sort_order
) VALUES (
    'copieur', 'personnel_scolaire', 'est utilise par', 'many_to_many', 'out',
    'Personnel scolaire', 0, 1,
    0, 0,
    'assignment', 'code_copieur',
    '', 40
)
ON DUPLICATE KEY UPDATE
    verb = VALUES(verb),
    display_label = VALUES(display_label),
    required = VALUES(required),
    is_active = VALUES(is_active),
    filter_candidates_by_shared_relation = VALUES(filter_candidates_by_shared_relation),
    show_indirect_relations = VALUES(show_indirect_relations),
    record_display_mode = VALUES(record_display_mode),
    assignment_resource_service_code = VALUES(assignment_resource_service_code),
    unique_value_field_key = VALUES(unique_value_field_key),
    sort_order = VALUES(sort_order);

-- Code copieur -> Personnel scolaire : seconde colonne de l'attribution.
INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction,
    display_label, required, is_active,
    filter_candidates_by_shared_relation, show_indirect_relations,
    record_display_mode, assignment_resource_service_code,
    unique_value_field_key, sort_order
) VALUES (
    'code_copieur', 'personnel_scolaire', 'est attribue a', 'many_to_one', 'out',
    'Personnel scolaire', 0, 1,
    0, 0,
    'standard', '',
    '', 30
)
ON DUPLICATE KEY UPDATE
    verb = VALUES(verb),
    display_label = VALUES(display_label),
    required = VALUES(required),
    is_active = VALUES(is_active),
    filter_candidates_by_shared_relation = VALUES(filter_candidates_by_shared_relation),
    show_indirect_relations = VALUES(show_indirect_relations),
    record_display_mode = VALUES(record_display_mode),
    assignment_resource_service_code = VALUES(assignment_resource_service_code),
    unique_value_field_key = VALUES(unique_value_field_key),
    sort_order = VALUES(sort_order);

COMMIT;
SET FOREIGN_KEY_CHECKS = @previous_foreign_key_checks;

-- Controle final : les relations historiques et scolaires doivent toutes
-- cibler le code technique unifie `copieur`.
SELECT code, label
FROM custom_services
WHERE code IN ('copieur', 'imprimante');

SELECT id, source_service_code, target_service_code, display_label,
       record_display_mode, assignment_resource_service_code,
       show_indirect_relations, is_active
FROM custom_service_relations
WHERE (source_service_code = 'copieur'
       AND target_service_code IN ('utilisateurs', 'services', 'personnel_scolaire_ou', 'personnel_scolaire'))
   OR (source_service_code = 'code_copieur'
       AND target_service_code IN ('copieur', 'utilisateurs', 'personnel_scolaire'))
   OR (source_service_code = 'personnel_scolaire'
       AND target_service_code = 'personnel_scolaire_ou')
ORDER BY source_service_code, target_service_code, id;

SELECT
    (SELECT COUNT(*) FROM custom_service_records WHERE service_code = 'copieur') AS copieurs,
    (SELECT COUNT(*) FROM custom_service_record_history WHERE service_code = 'copieur') AS historiques_copieurs,
    (SELECT COUNT(*) FROM custom_service_relation_links l
        JOIN custom_service_relations r ON r.id = l.relation_id
        WHERE r.source_service_code = 'copieur' OR r.target_service_code = 'copieur') AS liens_copieurs;
