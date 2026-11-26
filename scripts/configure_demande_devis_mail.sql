-- Modèle de départ du module No-Code. Conserve les personnalisations locales.
INSERT INTO notification_templates
    (code, label, module_code, task_type, subject_template, body_template, recipient, is_active, is_default)
SELECT 'demande-devis-texte', 'Demande de devis', 'demandes_de_devis', 'record:preview',
       'Demande de devis – {{record.fields.objet}}',
       'Bonjour,

Pourriez-vous nous transmettre un devis pour le besoin suivant ?

{{record.fields.description_besoin}}

Merci de préciser vos délais et la durée de validité du devis.

Cordialement,', '', 1, 0
FROM DUAL
WHERE EXISTS (SELECT 1 FROM custom_services WHERE code = 'demandes_de_devis')
  AND NOT EXISTS (SELECT 1 FROM notification_templates WHERE code = 'demande-devis-texte');
