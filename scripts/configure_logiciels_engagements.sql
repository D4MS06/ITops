-- ITops — configuration locale : modules Logiciels et Engagements
-- À exécuter après le démarrage initial d'ITops (schéma MariaDB déjà créé).
-- Le script est idempotent : il met à jour les éléments portant les mêmes clés.

START TRANSACTION;

INSERT INTO custom_services (
    code, label, is_active, is_technical, credentials_enabled, child_enabled,
    child_label, sort_order, icon, color, description, treeview_config,
    allow_export, allow_import, created_at, updated_at
) VALUES
(
    'logiciels', 'Logiciels', 1, 0, 0, 0, 'Éléments liés', 120, 'app', '',
    'Catalogue des logiciels, éditeurs, versions et licences.',
    '{"tile":{"show_count":true},"relationship_inheritance":{},"notification_rules":[],"automation_rules":[]}',
    1, 1, NOW(), NOW()
),
(
    'engagements', 'Engagements', 1, 0, 0, 0, 'Éléments liés', 130, 'contract', '',
    'Suivi des contrats, abonnements, renouvellements et montants.',
    '{"tile":{"show_count":true},"relationship_inheritance":{},"notification_rules":[],"automation_rules":[{"id":"echeance_j30","enabled":true,"trigger":{"type":"date","field_key":"date_echeance","offset_days":-30},"conditions":[{"field_key":"statut","operator":"not_equals","value":"Terminé"}],"actions":[{"type":"set_field","field_key":"statut","value":"À renouveler"},{"type":"notify"},{"type":"email","template_type":"engagement_echeance_j30","recipient_kind":"address","recipient_value":""}]},{"id":"echeance_depassee","enabled":true,"trigger":{"type":"date","field_key":"date_echeance","offset_days":0},"conditions":[{"field_key":"statut","operator":"not_equals","value":"Terminé"}],"actions":[{"type":"set_field","field_key":"statut","value":"Échu"},{"type":"notify"}]}]}',
    1, 1, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE
    label = VALUES(label), is_active = VALUES(is_active), icon = VALUES(icon), color = VALUES(color),
    description = VALUES(description), treeview_config = VALUES(treeview_config), updated_at = NOW();

-- Les tuiles du portail et leurs droits administrateur sont crees ici aussi.
-- Ainsi le script reste complet meme s'il est execute pendant que le service est deja demarre.
INSERT INTO auth_modules (code, label, route_path, is_active, sort_order) VALUES
    ('service_logiciels', 'Logiciels', '/#service=logiciels', 1, 1120),
    ('service_engagements', 'Engagements', '/#service=engagements', 1, 1130)
ON DUPLICATE KEY UPDATE
    label = VALUES(label), route_path = VALUES(route_path), is_active = VALUES(is_active), sort_order = VALUES(sort_order);

INSERT IGNORE INTO auth_role_modules (role_code, module_code) VALUES
    ('admin', 'service_logiciels'),
    ('admin', 'service_engagements');

-- Modele utilise par l'action e-mail de la regle d'echeance J-30.
-- Sans destinataire explicite, l'envoi utilise les destinataires SMTP par defaut
-- definis dans les parametres de notifications de l'application.
INSERT IGNORE INTO notification_templates (
    code, label, module_code, task_type, subject_template, body_template,
    is_active, is_default
) VALUES (
    'engagement_echeance_j30', 'Echeance d''engagement a J-30', 'engagements',
    'engagement_echeance_j30',
    'Echeance a renouveler dans 30 jours - {{record.id}}',
    'L''engagement {{record.id}} arrive a echeance dans 30 jours. Consultez la fiche Engagements pour preparer son renouvellement.',
    1, 0
);

INSERT INTO custom_service_fields (
    service_code, field_key, label, field_kind, required, options, default_value, sort_order,
    list_source_kind, shared_list_code, show_in_list, searchable, unique_value, placeholder,
    help_text, min_value, max_value, track_history, inline_editable, batch_editable, quick_filter
) VALUES
('logiciels','nom','Nom','text',1,'','',10,'local','',1,1,1,'','',NULL,NULL,1,1,0,0),
('logiciels','editeur','Éditeur','text',0,'','',20,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('logiciels','version','Version','text',0,'','',30,'local','',1,1,0,'','',NULL,NULL,1,1,0,0),
('logiciels','type_licence','Type de licence','list',0,'Propriétaire,Open source,SaaS,Gratuiciel','Propriétaire',40,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('logiciels','statut','Statut','list',1,'À évaluer,Validé,Déployé,Retiré','À évaluer',50,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('engagements','reference','Référence','text',1,'','',10,'local','',1,1,1,'','',NULL,NULL,1,1,0,0),
('engagements','objet','Objet','text',1,'','',20,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','fournisseur','Fournisseur','text',0,'','',30,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','statut','Statut','list',1,'Brouillon,Actif,À renouveler,Échu,Terminé','Brouillon',40,'local','',1,1,0,'','',NULL,NULL,1,1,1,1),
('engagements','date_debut','Date de début','date',0,'','',50,'local','',1,1,0,'','',NULL,NULL,1,1,0,0),
('engagements','date_echeance','Date d’échéance','date',1,'','',60,'local','',1,1,0,'','',NULL,NULL,1,1,0,1),
('engagements','montant_annuel','Montant annuel','number',0,'','',70,'local','',1,1,0,'','',0,NULL,1,1,0,0)
ON DUPLICATE KEY UPDATE
    label=VALUES(label), field_kind=VALUES(field_kind), required=VALUES(required), options=VALUES(options),
    default_value=VALUES(default_value), sort_order=VALUES(sort_order), show_in_list=VALUES(show_in_list),
    searchable=VALUES(searchable), track_history=VALUES(track_history), inline_editable=VALUES(inline_editable),
    batch_editable=VALUES(batch_editable), quick_filter=VALUES(quick_filter);

INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction, display_label,
    required, is_active, filter_candidates_by_shared_relation, show_indirect_relations, record_display_mode, sort_order
)
SELECT 'logiciels', 'engagements', 'est couvert par', 'many_to_many', 'out', 'Engagements associés',
       0, 1, 0, 0, 'standard', 10
WHERE NOT EXISTS (
    SELECT 1 FROM custom_service_relations
    WHERE source_service_code='logiciels' AND target_service_code='engagements' AND verb='est couvert par'
);

INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction, display_label,
    required, is_active, filter_candidates_by_shared_relation, show_indirect_relations, record_display_mode, sort_order
)
SELECT 'logiciels', 'utilisateurs', 'est utilise par', 'many_to_many', 'out', 'Agents associes',
       0, 1, 0, 0, 'standard', 20
WHERE NOT EXISTS (
    SELECT 1 FROM custom_service_relations
    WHERE source_service_code='logiciels' AND target_service_code='utilisateurs' AND verb='est utilise par'
);

INSERT INTO custom_service_relations (
    source_service_code, target_service_code, verb, cardinality, direction, display_label,
    required, is_active, filter_candidates_by_shared_relation, show_indirect_relations, record_display_mode, sort_order
)
SELECT 'logiciels', 'services', 'est utilise dans', 'many_to_many', 'out', 'Services associes',
       0, 1, 0, 0, 'standard', 30
WHERE NOT EXISTS (
    SELECT 1 FROM custom_service_relations
    WHERE source_service_code='logiciels' AND target_service_code='services' AND verb='est utilise dans'
);

-- Jeux de donnees de demonstration : chaque logiciel possede son engagement 2026.
-- Les identifiants stables rendent l'import rejouable sans dupliquer les fiches.
INSERT IGNORE INTO custom_service_records (
    id, service_code, payload_json, sync_source_kind, sync_target_kind, sync_external_id,
    sync_status, trashed_at, trash_reason, created_at, updated_at
) VALUES
('demo_logiciel_autocad', 'logiciels', JSON_OBJECT('nom', 'Autodesk AutoCAD', 'editeur', 'Autodesk', 'version', '2026', 'type_licence', 'Propriétaire', 'statut', 'Déployé'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_logiciel_adobe', 'logiciels', JSON_OBJECT('nom', 'Adobe Creative Cloud', 'editeur', 'Adobe', 'version', '2026', 'type_licence', 'SaaS', 'statut', 'Déployé'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_logiciel_eset', 'logiciels', JSON_OBJECT('nom', 'ESET PROTECT', 'editeur', 'ESET', 'version', '2026', 'type_licence', 'Propriétaire', 'statut', 'Déployé'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_logiciel_microsoft_365', 'logiciels', JSON_OBJECT('nom', 'Microsoft 365', 'editeur', 'Microsoft', 'version', '2026', 'type_licence', 'SaaS', 'statut', 'Déployé'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_logiciel_teamviewer', 'logiciels', JSON_OBJECT('nom', 'TeamViewer Tensor', 'editeur', 'TeamViewer', 'version', '2026', 'type_licence', 'SaaS', 'statut', 'Déployé'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_engagement_autocad_2026', 'engagements', JSON_OBJECT('reference', 'DEMO-AUTOCAD-2026', 'objet', 'Autodesk AutoCAD - renouvellement 2026', 'fournisseur', 'Cadline', 'statut', 'Échu', 'date_debut', '2026-01-01', 'date_echeance', '2026-10-31', 'montant_annuel', '3840.00'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_engagement_adobe_2026', 'engagements', JSON_OBJECT('reference', 'DEMO-ADOBE-2026', 'objet', 'Adobe Creative Cloud - renouvellement 2026', 'fournisseur', 'Adobe Business', 'statut', 'Échu', 'date_debut', '2025-12-01', 'date_echeance', '2026-09-30', 'montant_annuel', '8630.00'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_engagement_eset_2026', 'engagements', JSON_OBJECT('reference', 'DEMO-ESET-2026', 'objet', 'ESET PROTECT - renouvellement 2026', 'fournisseur', 'ESET France', 'statut', 'Échu', 'date_debut', '2025-04-01', 'date_echeance', '2026-03-31', 'montant_annuel', '4935.00'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_engagement_microsoft_365_2026', 'engagements', JSON_OBJECT('reference', 'DEMO-M365-2026', 'objet', 'Microsoft 365 - renouvellement 2026', 'fournisseur', 'Microsoft CSP', 'statut', 'Échu', 'date_debut', '2025-02-01', 'date_echeance', '2026-01-31', 'montant_annuel', '18612.00'), '', '', '', 'active', NULL, '', NOW(), NOW()),
('demo_engagement_teamviewer_2026', 'engagements', JSON_OBJECT('reference', 'DEMO-TEAMVIEWER-2026', 'objet', 'TeamViewer Tensor - renouvellement 2026', 'fournisseur', 'TeamViewer France', 'statut', 'Échu', 'date_debut', '2025-06-01', 'date_echeance', '2026-05-31', 'montant_annuel', '2256.00'), '', '', '', 'active', NULL, '', NOW(), NOW());

INSERT INTO custom_service_record_index (record_id, service_code, label_value, search_blob, indexed_at) VALUES
('demo_logiciel_autocad', 'logiciels', 'Autodesk AutoCAD', 'Logiciels Autodesk AutoCAD Autodesk 2026 Proprietaire Deployee', NOW()),
('demo_logiciel_adobe', 'logiciels', 'Adobe Creative Cloud', 'Logiciels Adobe Creative Cloud Adobe 2026 SaaS Deployee', NOW()),
('demo_logiciel_eset', 'logiciels', 'ESET PROTECT', 'Logiciels ESET PROTECT ESET 2026 Proprietaire Deployee', NOW()),
('demo_logiciel_microsoft_365', 'logiciels', 'Microsoft 365', 'Logiciels Microsoft 365 Microsoft 2026 SaaS Deployee', NOW()),
('demo_logiciel_teamviewer', 'logiciels', 'TeamViewer Tensor', 'Logiciels TeamViewer Tensor TeamViewer 2026 SaaS Deployee', NOW()),
('demo_engagement_autocad_2026', 'engagements', 'DEMO-AUTOCAD-2026', 'Engagements DEMO-AUTOCAD-2026 Autodesk AutoCAD renouvellement 2026 Cadline Echu', NOW()),
('demo_engagement_adobe_2026', 'engagements', 'DEMO-ADOBE-2026', 'Engagements DEMO-ADOBE-2026 Adobe Creative Cloud renouvellement 2026 Adobe Business Echu', NOW()),
('demo_engagement_eset_2026', 'engagements', 'DEMO-ESET-2026', 'Engagements DEMO-ESET-2026 ESET PROTECT renouvellement 2026 ESET France Echu', NOW()),
('demo_engagement_microsoft_365_2026', 'engagements', 'DEMO-M365-2026', 'Engagements DEMO-M365-2026 Microsoft 365 renouvellement 2026 Microsoft CSP Echu', NOW()),
('demo_engagement_teamviewer_2026', 'engagements', 'DEMO-TEAMVIEWER-2026', 'Engagements DEMO-TEAMVIEWER-2026 TeamViewer Tensor renouvellement 2026 TeamViewer France Echu', NOW())
ON DUPLICATE KEY UPDATE
    service_code = VALUES(service_code), label_value = VALUES(label_value), search_blob = VALUES(search_blob), indexed_at = VALUES(indexed_at);

INSERT IGNORE INTO custom_service_relation_links (relation_id, source_record_id, target_record_id)
SELECT relation.id, links.logiciel_id, links.engagement_id
FROM custom_service_relations AS relation
JOIN (
    SELECT 'demo_logiciel_autocad' AS logiciel_id, 'demo_engagement_autocad_2026' AS engagement_id
    UNION ALL SELECT 'demo_logiciel_adobe', 'demo_engagement_adobe_2026'
    UNION ALL SELECT 'demo_logiciel_eset', 'demo_engagement_eset_2026'
    UNION ALL SELECT 'demo_logiciel_microsoft_365', 'demo_engagement_microsoft_365_2026'
    UNION ALL SELECT 'demo_logiciel_teamviewer', 'demo_engagement_teamviewer_2026'
) AS links
WHERE relation.source_service_code = 'logiciels'
  AND relation.target_service_code = 'engagements'
  AND relation.cardinality = 'many_to_many'
  AND relation.direction = 'out';

COMMIT;
