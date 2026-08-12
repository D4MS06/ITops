-- Configuration autonome à exécuter une seule fois sur la base MariaDB iTOPS.
--
-- Pré-requis : les modules suivants existent déjà :
--   personnel_scolaire, personnel_scolaire_ou, copieur, code_copieur.
--
-- Ce script ne fait partie d'aucune migration automatique de l'application.
-- Il est idempotent : une nouvelle exécution met à jour les relations visées
-- sans supprimer les liens déjà saisis entre les fiches.

START TRANSACTION;

-- Permet d'afficher, depuis une fiche Personnel scolaire, les copieurs liés
-- à son école. Les relations directes restent affichées séparément.
UPDATE custom_service_relations
SET show_indirect_relations = 1,
    is_active = 1
WHERE source_service_code = 'personnel_scolaire'
  AND target_service_code = 'personnel_scolaire_ou'
  AND direction = 'out';

-- Une école peut avoir plusieurs copieurs ; un copieur est installé dans une
-- seule école. Les liens se configurent ensuite dans la fiche du copieur.
INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction,
    display_label, required, is_active,
    filter_candidates_by_shared_relation, show_indirect_relations,
    record_display_mode, assignment_resource_service_code,
    unique_value_field_key, sort_order
) VALUES (
    'copieur', 'personnel_scolaire_ou', 'est installe dans', 'many_to_one', 'out',
    'Ecole', 0, 1,
    0, 0,
    'standard', '',
    '', 30
)
ON DUPLICATE KEY UPDATE
    verb = VALUES(verb),
    display_label = VALUES(display_label),
    is_active = VALUES(is_active),
    record_display_mode = VALUES(record_display_mode),
    sort_order = VALUES(sort_order);

-- Un copieur peut être utilisé par plusieurs membres du personnel, et une
-- personne peut utiliser plusieurs copieurs.
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
    'standard', '',
    '', 40
)
ON DUPLICATE KEY UPDATE
    verb = VALUES(verb),
    display_label = VALUES(display_label),
    is_active = VALUES(is_active),
    record_display_mode = VALUES(record_display_mode),
    sort_order = VALUES(sort_order);

-- Un code personnel est attribué à une seule personne. Un membre du
-- personnel peut naturellement posséder plusieurs codes.
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
    is_active = VALUES(is_active),
    record_display_mode = VALUES(record_display_mode),
    sort_order = VALUES(sort_order);

COMMIT;

-- Contrôle attendu : quatre lignes au total, dont les trois relations
-- créées ci-dessus et la relation Personnel scolaire -> Ecoles.
SELECT id, source_service_code, target_service_code, display_label,
       cardinality, direction, show_indirect_relations, is_active
FROM custom_service_relations
WHERE (source_service_code = 'personnel_scolaire'
       AND target_service_code = 'personnel_scolaire_ou')
   OR (source_service_code = 'copieur'
       AND target_service_code IN ('personnel_scolaire_ou', 'personnel_scolaire'))
   OR (source_service_code = 'code_copieur'
       AND target_service_code = 'personnel_scolaire')
ORDER BY source_service_code, target_service_code;
