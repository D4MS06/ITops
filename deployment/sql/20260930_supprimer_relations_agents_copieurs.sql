-- Verification de production : Copieurs et Personnel scolaire.
--
-- DEPRECIEE COMME MIGRATION DE SUPPRESSION : un copieur peut etre utilise a
-- la fois par des Agents et du Personnel scolaire. Les deux relations sont
-- donc legitimes et doivent rester en place.
--
-- Ce script est volontairement non destructif. Il produit seulement les
-- compteurs utiles pour analyser l'affichage des relations.

START TRANSACTION;

SELECT
    r.id,
    r.source_service_code,
    r.target_service_code,
    r.display_label,
    r.record_display_mode,
    r.assignment_resource_service_code,
    COUNT(l.id) AS link_count
FROM custom_service_relations r
LEFT JOIN custom_service_relation_links l ON l.relation_id = r.id
WHERE r.source_service_code IN ('copieur', 'code_copieur')
  AND r.target_service_code IN ('utilisateurs', 'personnel_scolaire')
GROUP BY r.id, r.source_service_code, r.target_service_code, r.display_label,
         r.record_display_mode, r.assignment_resource_service_code
ORDER BY r.source_service_code, r.target_service_code, r.id;

COMMIT;
