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
            // Dans la même image, sans yield : les deux textes tels que la photo les montre.
            var textes = Lot658.toile != null ? Lot658.toile.GetComponentsInChildren<Text>(true) : throw Echec("toile du cabinet absente");
            var legende = textes.FirstOrDefault(t => t.name == "Légende des lieux") ?? throw Echec("légende des lieux absente"); string lieux = legende.text; Lot690.DansLeChamp(camera, legende);
            string cache = Lot658.toile.GetComponentsInChildren<Image>(false).Where(i => i.raycastTarget && Recouvre(camera, i.rectTransform, legende.rectTransform)).Select(i => i.name).FirstOrDefault();
            if (cache != null) throw Echec("légende des lieux cachée sous « " + cache + " »");
            string fleches = (textes.FirstOrDefault(t => t.name == "Légende des flèches") ?? throw Echec("légende des flèches absente")).text;
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
