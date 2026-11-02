using System; using System.Collections; using System.Globalization; using System.Linq;
using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 963 : la carte en mode Habitants, la bande des modes en bas à droite, sa légende au-dessus, « Les autres maisons » ouvert, les dossiers entiers, rien de caché.
    // Changer de mode ne relit rien et ne touche pas l'horloge : `-forge963Relire` lance une lecture juste après les clics, et la capture rougit.
    static class Lot963 {
        const string RELIRE = "-forge963Relire"; static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ligne(string t) => (t ?? "(aucun)").Replace("\r", "").Replace("\n", " | ");
        static Rect Ecran(Camera camera, RectTransform cadre) { var coins = new Vector3[4]; cadre.GetWorldCorners(coins); var p = coins.Select(c => camera.WorldToScreenPoint(c)).ToArray(); return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y)); }
        [ScenarioDeCapture(963, "mode-habitants")] static IEnumerator ModeHabitants(Camera camera) {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; CarteDessinee carte = ouverte.Carte;
            CabinetDeCarte cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de CabinetDeCarte"); HorlogeDeCarte horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas d'horloge");
            CalquesCarte calques = carte.GetComponent<CalquesCarte>() ?? throw Echec("étape 1 : le cabinet n'a pas de CalquesCarte"); (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : la carte n'a pas de parcours")).automatique = true;
            Transform toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("étape 1 : la toile du cabinet n'est pas active");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 1 : " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            Button Bouton(string parent, string nom) => toile.Find(parent)?.Find(nom)?.GetComponent<Button>() ?? throw Echec("« " + parent + "/" + nom + " » introuvable"); Bouton("Parcourir le monde", "Autres maisons").onClick.Invoke();
            for (var e = Lot690.Jusqua(() => !cabinet.Partie.Occupee && horloge.Lue != null, () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie) + ", horloge " + (horloge.Lue == null ? "non lue" : "lue")); e.MoveNext();) yield return null;
            // Étape 3, dans une même image, sans yield : les clics des trois modes ne relisent rien et ne touchent pas l'horloge.
            HorlogeLue lue = horloge.Lue; long tick = lue.Tick; double vitesse = lue.JoursParSeconde; var monde = cabinet.Partie.Monde; bool occupee = cabinet.Partie.Occupee;
            foreach (string mode in new[] { "Flux", "Puissances", "Habitants" }) Bouton(CalquesCarte.BANDE, mode).onClick.Invoke(); if (Environment.GetCommandLineArgs().Contains(RELIRE)) _ = cabinet.Partie.Actualiser();
            string ecart = !ReferenceEquals(horloge.Lue, lue) ? "horloge relue" : horloge.Lue.Tick != tick || horloge.Lue.JoursParSeconde != vitesse ? "horloge changée"
                : !ReferenceEquals(cabinet.Partie.Monde, monde) ? "monde relu" : cabinet.Partie.Occupee != occupee ? "lecture de la partie lancée" : null;
            if (ecart != null) throw Echec("le changement de mode a relancé une lecture du monde ou touché l'horloge : " + ecart); if (calques.Mode != ModeDeCarte.Habitants) throw Echec("étape 3 : mode " + calques.Mode + " après le clic sur Habitants");
            RepartitionHabitants repartition = null; MondeLu lu = null; // étape 4 : la légende des habitants du monde lu, et les terres du clair au foncé
            string Attendue() { var m = cabinet.Partie.Monde; if (m?.Presente != true) return null; lu = m.Donnees.Monde; repartition = new RepartitionHabitants(lu); return CalquesCarte.LegendeDuMode(ModeDeCarte.Habitants, repartition); }
            for (var e = Lot690.Jusqua(() => calques.Legende != null && calques.Legende.text == Attendue(), () => "étape 4 : légende « " + Ligne(calques.Legende?.text) + " », attendu « " + Ligne(Attendue()) + " »"); e.MoveNext();) yield return null;
            string legende = calques.Legende.text; if ((TexteDuMonde.Interdit(legende) ?? TexteDuMonde.SansUnite(legende)) is string mot) throw Echec("étape 4 : « " + mot + " » refusé dans la légende « " + Ligne(legende) + " »");
            int lignes = Math.Max(CalquesCarte.Lignes(calques.Legende, legende, 1f), CalquesCarte.Lignes(calques.Legende, legende, 2f / 3f)); if (lignes > CalquesCarte.LIGNES_MAX) throw Echec("étape 4 : légende de " + lignes + " lignes : « " + Ligne(legende) + " »");
            long? gardee = cabinet.Retenue?.CellId; var cellules = carte.transform.Find("Cellules de la carte") ?? throw Echec("étape 4 : « Cellules de la carte » introuvable");
            long id = cellules.GetComponentsInChildren<MeshRenderer>().Select(r => long.Parse(r.name.Substring("Cellule ".Length), CultureInfo.InvariantCulture)).Where(c => c != gardee).Min();
            Color vue = cellules.Find("Cellule " + id.ToString(CultureInfo.InvariantCulture)).GetComponent<MeshRenderer>().sharedMaterial.color, voulue = CalquesCarte.Teinte(ModeDeCarte.Habitants, false, default, repartition.Position(id));
            if (Mathf.Abs(vue.r - voulue.r) > .01f || Mathf.Abs(vue.g - voulue.g) > .01f || Mathf.Abs(vue.b - voulue.b) > .01f) throw Echec("étape 4 : la terre " + id.ToString(CultureInfo.InvariantCulture) + " est en " + vue + ", attendu " + voulue);
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f); camera.aspect = Lot549.FORME; Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; // étape 5, comme Lot943, sans rien cacher
            yield return null; Canvas.ForceUpdateCanvases(); for (int i = 0; i < 10; i++) yield return null; var image = new Rect(0, 0, camera.pixelWidth, camera.pixelHeight); // étape 6 : entières, sur aucun panneau
            foreach (string zone in new[] { CalquesCarte.LEGENDE, CalquesCarte.BANDE }) {
                Rect r = Ecran(camera, (RectTransform)(toile.Find(zone) ?? throw Echec("étape 6 : « " + zone + " » introuvable")));
                if (r.xMin < -.5f || r.yMin < -.5f || r.xMax > image.xMax + .5f || r.yMax > image.yMax + .5f) throw Echec("étape 6 : « " + zone + " » hors de l'image : " + r + " dans " + image);
                foreach (string panneau in new[] { "Les autres maisons", "Votre maison", "Territoire conservé", "FORGE · Le cabinet", "Parcourir le monde" }) {
                    var cadre = (RectTransform)(toile.Find(panneau) ?? throw Echec("étape 6 : « " + panneau + " » introuvable")); if (!cadre.gameObject.activeInHierarchy) throw Echec("étape 6 : « " + panneau + " » caché");
                    if (r.Overlaps(Ecran(camera, cadre))) throw Echec("étape 6 : « " + zone + " » recouvre « " + panneau + " »"); } }
            Debug.Log("CAPTURE_963 mode Habitants · légende « " + Ligne(legende) + " » · lignes " + lignes + " · tick " + lu.Tick.ToString(CultureInfo.InvariantCulture));
        }
    }
}
