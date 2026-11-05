using System;
using System.Collections;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
namespace ForgeLocal3D.Captures
{
    // Lot 875 : la photo du lot 658 (Mistra, 60 %, trente jours, le feuillet ouvert), puis les deux légendes jugées en noms et en unités.
    // `-forge875Identifiant` glisse le couple d'une flèche dans la légende des flèches : la capture doit échouer sur « mot interdit ».
    static class Lot875
    {
        const string SIEGE = "Mistra", IDENTIFIANT = "-forge875Identifiant", PREFIXE = "Flèche ";
        static InvalidOperationException Echec(string c) => new InvalidOperationException(c);
        static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        [ScenarioDeCapture(875, "legendes-en-noms")] static IEnumerator LegendesEnNoms(Camera camera)
        {
            for (var e = Lot658.FlechesDuSiege(camera); e.MoveNext();) yield return null;
            // Le feuillet, contrôlé ouvert par le lot 658, couvre la légende des lieux (en haut à gauche) : il se ferme pour que la photo la montre entière.
            var feuillet = Lot658.toile.Cast<Transform>().FirstOrDefault(t => t.name == "Terres et comptes" && t.GetComponentInChildren<ScrollRect>(true) != null) ?? throw Echec("feuillet « Terres et comptes » introuvable");
            (feuillet.GetComponentsInChildren<Button>(true).FirstOrDefault(b => b.name == "Fermer") ?? throw Echec("feuillet sans « Fermer »")).onClick.Invoke();
            for (int i = 0; i < 5; i++) yield return null; if (feuillet.gameObject.activeInHierarchy) throw Echec("feuillet resté ouvert sur la légende des lieux");
            // Lot #964 : les deux légendes sont l'infobulle de la légende du mode, en Flux puis en Puissances.
            var calques = Lot658.carte.GetComponent<CalquesCarte>() ?? throw Echec("pas de CalquesCarte"); var legende = calques.Legende; var bulle = Lot658.toile.Find(CalquesCarte.LEGENDE)?.GetComponent<Infobulle>() ?? throw Echec("légende du mode sans infobulle");
            if (calques.Mode != ModeDeCarte.Flux || legende.text != CalquesCarte.FLUX) throw Echec("légende du Flux « " + Ligne(legende.text) + " » en mode " + calques.Mode); string fleches = bulle.Phrase, puissances = CalquesCarte.LegendeDuMode(ModeDeCarte.Puissances, null, true);
            (Lot658.toile.Find(CalquesCarte.BANDE)?.Find("Puissances")?.GetComponent<Button>() ?? throw Echec("bouton « Puissances » introuvable")).onClick.Invoke();
            for (var e = Lot690.Jusqua(() => legende.text == puissances && bulle.Phrase != null && bulle.Phrase.Contains("· relevé au jour"), () => "légende des Puissances « " + Ligne(legende.text) + " », infobulle « " + Ligne(bulle.Phrase) + " »"); e.MoveNext();) yield return null;
            // Dans la même image, sans yield : la légende telle que la photo la montre.
            string lieux = bulle.Phrase; Lot690.DansLeChamp(camera, legende);
            string cache = Lot658.toile.GetComponentsInChildren<Image>(false).Where(i => i.raycastTarget && i.name != CalquesCarte.LEGENDE && Recouvre(camera, i.rectTransform, legende.rectTransform)).Select(i => i.name).FirstOrDefault();
            if (cache != null) throw Echec("légende des lieux cachée sous « " + cache + " »");
            if (Environment.GetCommandLineArgs().Contains(IDENTIFIANT))
            {
                // La flèche du dû n'a pas de couple : le premier objet d'un lieu (« Flèche 10340-1 » donne « 10340-1 »).
                var racine = Lot658.carte.transform.Find(FlechesDeCarte.RACINE) ?? throw Echec("aucune flèche sous « " + FlechesDeCarte.RACINE + " »");
                var lieu = racine.Cast<Transform>().FirstOrDefault(t => t.name != FlechesDeCarte.DU && t.name.StartsWith(PREFIXE, StringComparison.Ordinal)) ?? throw Echec("aucune flèche de lieu sous « " + FlechesDeCarte.RACINE + " »");
                fleches += "\nLieu " + lieu.name.Substring(PREFIXE.Length);
            }
            Exiger("légende des lieux", lieux, "· relevé au jour"); Exiger("légende des flèches", fleches, "→ " + SIEGE + " : ", "de dû");
            Debug.Log("CAPTURE_875 légende des lieux « " + Ligne(lieux) + " »"); Debug.Log("CAPTURE_875 légende des flèches « " + Ligne(fleches) + " »");
        }
        static Rect Cadre(Camera camera, RectTransform r) { var c = new Vector3[4]; r.GetWorldCorners(c); var p = c.Select(q => camera.WorldToViewportPoint(q)).ToArray(); return Rect.MinMaxRect(p.Min(q => q.x), p.Min(q => q.y), p.Max(q => q.x), p.Max(q => q.y)); }
        // Un panneau qui prend les clics et passe sur la ligne du texte réellement écrite (sa hauteur préférée), pas sur le cadre vide sous elle.
        static bool Recouvre(Camera camera, RectTransform panneau, RectTransform texte) { var t = Cadre(camera, texte); var h = texte.GetComponent<Text>().preferredHeight / Mathf.Max(texte.rect.height, 1f); return Cadre(camera, panneau).Overlaps(Rect.MinMaxRect(t.xMin, t.yMax - t.height * Mathf.Min(1f, h), t.xMax, t.yMax)); }
        static void Exiger(string quoi, string texte, params string[] attendus)
        {
            foreach (var a in attendus) if (!texte.Contains(a)) throw Echec(quoi + " sans « " + a + " » : « " + Ligne(texte) + " »");
            string mot = TexteDuMonde.Interdit(texte); if (mot != null) throw Echec("mot interdit « " + mot + " » : « " + Ligne(texte) + " »");
            string nu = TexteDuMonde.SansUnite(texte); if (nu != null) throw Echec(quoi + " : nombre sans unité « " + nu + " » : « " + Ligne(texte) + " »");
        }
    }
}
