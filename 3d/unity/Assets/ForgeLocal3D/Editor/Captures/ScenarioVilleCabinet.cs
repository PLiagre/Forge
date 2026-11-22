using System;
using System.Collections;
using System.Linq;
using System.Text.RegularExpressions;
using Forge.Interface;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // La ville du désert avec son cabinet : « Le bourg » et la barre des outils posés sur l'image, et plus
    // aucun texte de mise au point. La caméra descend vers la ville ; la photo n'est prise que lorsque le
    // feuillet du bourg a fini de se lire (les textes du cabinet sont récrits une image après la lecture du
    // lieu), puis le scénario refuse tout texte de mise au point encore visible.
    static class ScenarioVilleCabinet
    {
        const float INCLINAISON = 35f;
        const float DISTANCE_M = 140f;
        const double STABLE_S = 2.5;
        const double BORNE_S = 40;
        const string EN_ATTENTE = "… En attente";
        const string PANNE = "! Le monde ne répond pas";
        static readonly Regex MiseAuPoint = new Regex(@"Cellule\s+[0-9]|·\s*tick", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        [ScenarioDeCapture("ville-cabinet", "capitale")]
        static IEnumerator Capitale(Camera camera)
        {
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            if (ville == null)
                throw new InvalidOperationException("la scène n'a pas de DesertCityCamera");
            var cabinet = Object.FindFirstObjectByType<CabinetDeVille>();
            if (cabinet == null)
                throw new InvalidOperationException("la scène n'a pas de CabinetDeVille : le cabinet de la ville n'est pas posé");
            double debut = Time.realtimeSinceStartupAsDouble, change = debut;
            // La capitale, c'est son bourg de 1400 : la caméra se pose sur ses maisons dès qu'elles sont dessinées.
            var outil = Object.FindFirstObjectByType<DesertRoadTool>();
            Renderer[] maisons = new Renderer[0];
            while ((maisons = outil?.Maisons?.Racine != null ? outil.Maisons.Racine.GetComponentsInChildren<Renderer>() : new Renderer[0]).Length == 0
                   && Time.realtimeSinceStartupAsDouble - debut < BORNE_S / 2) yield return null;
            if (maisons.Length > 0)
            {
                var boite = maisons[0].bounds; foreach (var r in maisons) boite.Encapsulate(r.bounds);
                ville.Poser(boite.center, ville.Cap, INCLINAISON, Mathf.Clamp(boite.extents.magnitude * 2.2f, DISTANCE_M, DesertCityCamera.DistanceMax));
            }
            else ville.VueEnsemble();

            change = Time.realtimeSinceStartupAsDouble;
            string vu = null;
            while (true)
            {
                double maintenant = Time.realtimeSinceStartupAsDouble;
                string texte = cabinet.TexteDuBourg ?? "";
                if (texte != vu) { vu = texte; change = maintenant; }
                if (!texte.StartsWith(EN_ATTENTE, StringComparison.Ordinal) && maintenant - change >= STABLE_S) break;
                if (maintenant - debut > BORNE_S)
                    throw new TimeoutException("le feuillet « Le bourg » devait quitter « " + EN_ATTENTE + " » et rester identique " + STABLE_S
                        + " s, en " + BORNE_S + " s ; dernier texte : « " + vu + " »");
                yield return null;
            }
            if (vu.StartsWith(PANNE, StringComparison.Ordinal))
                throw new InvalidOperationException("le feuillet « Le bourg » n'a pas lu le lieu : " + vu);

            // Le feuillet du bourg et la barre des outils passent les juges du clerc, ligne à ligne : ni identifiant, ni mot de mise
            // au point, ni nombre sans unité. Un libellé se lit sans son raccourci : « (4) » nomme une touche, pas un nombre du monde.
            // Le grand feuillet d'aide du tracé n'a plus sa place : la ligne de la barre le remplace.
            if (cabinet.FeuilletDesOutils.gameObject.activeInHierarchy)
                throw new InvalidOperationException("le feuillet « " + CabinetDeVille.OUTILS + " » est encore visible : « " + cabinet.TexteDesOutils + " »");
            var composition = outil?.Recomposer() ?? throw new InvalidOperationException("la ville n'a pas de barre des outils");
            var barre = composition.Boutons.Where(b => b.Visible).Select(b => b.Libelle.Replace(Forge.Pont.OutilsDeLaVille.Libelle(b.Geste), ""))
                .Append(outil.Barre.Ligne.text);
            foreach (string ecrit in cabinet.TexteDuBourg.Split('\n').Concat(barre.SelectMany(t => t.Split('\n'))).Where(l => l.Length > 0))
            {
                string faute = Forge.Pont.TexteDuMonde.Interdit(ecrit ?? "") ?? Forge.Pont.TexteDuMonde.SansUnite(ecrit ?? "");
                if (faute != null) throw new InvalidOperationException("« " + faute + " » dans un feuillet du cabinet : « " + ecrit + " »");
            }
            string reste = TexteDeMiseAuPointVisible();
            if (reste != null)
                throw new InvalidOperationException("un texte de mise au point est encore visible : « " + reste + " »");
        }

        // Le premier texte visible à l'image qui dit « Cellule <nombre> » ou « · tick » ; null s'il n'y en a pas.
        static string TexteDeMiseAuPointVisible()
        {
            foreach (var t in Object.FindObjectsByType<Text>(FindObjectsSortMode.None))
                if (t.isActiveAndEnabled && t.GetComponentsInParent<Canvas>().All(c => c.enabled) && MiseAuPoint.IsMatch(t.text))
                    return t.name + " : " + t.text;
            foreach (var t in Object.FindObjectsByType<TextMesh>(FindObjectsSortMode.None))
            {
                var rendu = t.GetComponent<MeshRenderer>();
                if (rendu != null && rendu.enabled && t.gameObject.activeInHierarchy && MiseAuPoint.IsMatch(t.text))
                    return t.name + " : " + t.text;
            }
            return null;
        }
    }
}
