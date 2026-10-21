using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
namespace ForgeLocal3D.Captures
{
    // Lot 658 : Mistra, prélèvement à 60 %, trente ticks, le feuillet ouvert ; les flèches contrôlées contre des lectures indépendantes. `-forge658RetirerDu` éteint la vraie flèche du dû.
    static class Lot658
    {
        const string SIEGE = "Mistra", RETIRER = "-forge658RetirerDu", TICKS_ARG = "-forgeTicks",CONFIRMER = "Confirmer l’ordre", FEUILLET = "Terres et comptes"; const int IMAGES = 10, TICKS = 30; const float R = ReperesDeDepart.DIAMETRE_BORD_KM / 2f;
        static CarteDessinee carte; static Transform toile, racine; static string N(long v) => v.ToString(Inv); static readonly CultureInfo Inv = CultureInfo.InvariantCulture, Fr = CultureInfo.GetCultureInfo("fr-FR"); static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static InvalidOperationException Echec(string c) => new InvalidOperationException(c); // Le parcours part du tick demandé au service : `-forgeTicks` (0 dans SC5), sinon le défaut de `ForgeCapture` (30), que le pilote du PC laisse.
        static long Depart() { var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG); return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 30; }
        sealed class Attendu { public string Haut; public PointCarte Siege, PHaut; public double Preleve, Du, SurPlace = -1; public List<long> Cells = new List<long>(); public List<(string couple, PointCarte p, double kg)> Lieux = new List<(string, PointCarte, double)>(); }
        [ScenarioDeCapture(658, "fleches-du-siege")] static IEnumerator FlechesDuSiege(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; int port = carte.port; var cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("pas de cabinet"); if (carte.GetComponents<FlechesDeCarte>().Length != 1) throw Echec("vue des flèches absente ou multiple");
            var vue = carte.GetComponent<FlechesDeCarte>(); var disques = carte.GetComponent<LieuxDeCarte>(); var dossier = carte.GetComponent<DossierMaison>() ?? throw Echec("pas de DossierMaison");
            toile = carte.transform.Find("Cabinet"); var commandes = carte.GetComponent<CommandesMaison>(); racine = toile != null ? toile.Find("Votre maison/Commandes de maison") : null; if (racine == null || commandes == null) throw Echec("commandes introuvables");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            var partie = cabinet.Partie; var mistra = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray(); if (mistra.Length != 1) throw Echec(mistra.Length + " départs " + SIEGE);
            long tick = partie.Monde.Donnees.Monde.Tick, depart = Depart(); if (tick != depart) throw Echec("tick initial " + N(tick) + ", attendu " + N(depart) + " (" + TICKS_ARG + ")"); var choix = partie.Choisir(mistra[0].Id); for (var e = Lot690.Attendre(choix, "choix"); e.MoveNext();) yield return null;
            if (partie.Recu == null || !partie.Recu.Acceptee || partie.Recu.AppliqueeAuTick != tick) throw Echec("reçu du choix refusé");
            var un = Lot690.PousserTick(port); for (var e = Lot690.Attendre(un, "tick"); e.MoveNext();) yield return null; if (un.Result.statut != 200) throw Echec("tick " + un.Result.corps);
            for (var e = Lot690.Jusqua(() => Bouton("Prélèvement").interactable && partie.Maison?.Presente == true && partie.Maison.Donnees.Siege.Nom == SIEGE && partie.Monde.Donnees.MaisonDuJoueur == partie.Maison.Donnees.Id && partie.Monde.Donnees.Monde.Tick == tick + 1, () => "maison « " + (partie.Maison?.Absence ?? "") + " »"); e.MoveNext();) yield return null;
            string maison = partie.Maison.Donnees.Id; Bouton("Prélèvement").onClick.Invoke(); yield return null;
            var curseur = racine.GetComponentInChildren<Slider>(true); if (curseur == null || !curseur.gameObject.activeInHierarchy) throw Echec("curseur invisible");
            curseur.value = 60; yield return null; if (Math.Abs(curseur.value - 60f) > 0.01f) throw Echec("curseur " + curseur.value); Bouton("Préparer").onClick.Invoke(); yield return null; Bouton(CONFIRMER).onClick.Invoke();
            for (var e = Lot690.Jusqua(() => commandes.Ordre.Recu != null && commandes.Ordre.Recu.Acceptee, () => "reçu « " + Ligne(commandes.MessageAffiche) + " »"); e.MoveNext();) yield return null;
            long fin = commandes.Ordre.Recu.AppliqueeAuTick.Value + TICKS; if (fin != depart + 1 + TICKS) throw Echec("ordre reçu au tick " + N(fin - TICKS) + ", attendu " + N(depart + 1)); var trente = Task.Run(() => { for (int i = 0; i < TICKS; i++) { var r = Lot690.PousserTick(port).Result; if (r.statut != 200) return r; } return (200, ""); });
            for (var e = Lot690.Attendre(trente, "trente ticks"); e.MoveNext();) yield return null; if (trente.Result.Item1 != 200) throw Echec("tick " + trente.Result.Item2);
            var bouton = toile.GetComponentsInChildren<Button>(true).Where(b => b.name == FEUILLET).ToArray(); if (bouton.Length != 1 || !bouton[0].interactable) throw Echec(bouton.Length + " boutons « " + FEUILLET + " »"); bouton[0].onClick.Invoke();
            var lu = Task.Run(() => Lire(port, maison, fin)); for (var e = Lot690.Attendre(lu, "lectures indépendantes"); e.MoveNext();) yield return null; var at = lu.Result;
            string[] lignes = at.Lieux.Select(l => "\nLieu " + l.couple + " → " + SIEGE + " : " + FlechesDeCarte.Kg(l.kg)).Concat(new[] { "\n" + SIEGE + " : " + FlechesDeCarte.Kg(at.SurPlace) + " prélevés sur place", "\n" + SIEGE + " → " + at.Haut + " : " + FlechesDeCarte.Kg(at.Du) + " de dû" }).ToArray();
            string[] feuillet = { " · tick " + N(fin) + Environment.NewLine, "Prélevé : " + at.Preleve.ToString("0.##", Fr) + " kg" + Environment.NewLine, "Dû envoyé : " + at.Du.ToString("0.##", Fr) + " kg" + Environment.NewLine };
            for (var e = Lot690.Jusqua(() => vue.TexteLegende != null && lignes.All(vue.TexteLegende.Contains) && disques.TexteLegende != null && at.Cells.All(c => disques.TexteLegende.Contains("\nCellule " + N(c) + " au tick " + N(fin))) && dossier.TexteAffiche != null && feuillet.All(dossier.TexteAffiche.Contains),
                () => "flèches « " + Ligne(vue.TexteLegende) + " » feuillet « " + Ligne(dossier.TexteAffiche) + " » attendu « " + Ligne(string.Join("", lignes)) + " »"); e.MoveNext();) yield return null;
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f); var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases(); Cadrer(camera, at); yield return null; var mesures = Controler(camera, at);
            if (Environment.GetCommandLineArgs().Contains(RETIRER)) { var du = carte.transform.Find(FlechesDeCarte.RACINE + "/" + FlechesDeCarte.DU); if (du != null) du.gameObject.SetActive(false); }
            for (int i = 0; i < IMAGES; i++) yield return null; mesures = Controler(camera, at);
            Debug.Log("CAPTURE_658 maison " + maison + ", départ au tick " + N(depart) + ", tick " + N(fin) + ", " + mesures + ", sur place " + at.SurPlace.ToString("0", Inv) + " kg");
        }
        static Vector3 Monde(PointCarte p) => carte.transform.TransformPoint(carte.PositionSurLaCarte(p, FlechesDeCarte.HAUTEUR).Value);
        // Le siège et ses lieux dans la bande libre entre le feuillet, les dossiers, les légendes et le bandeau, avec une marge.
        static void Cadrer(Camera camera, Attendu at)
        {
            float x0 = 764f / 1920f + 0.01f, x1 = 0.66f, y0 = 0f, y1 = 1f; foreach (var c in Caches(camera)) if (c.xMax > x0 && c.xMin < x1) { if (c.yMax < 0.5f) y0 = Mathf.Max(y0, c.yMax); else if (c.yMin > 0.5f) y1 = Mathf.Min(y1, c.yMin); }
            var pts = at.Lieux.Select(l => carte.PositionSurLaCarte(l.p, 0f).Value).Append(carte.PositionSurLaCarte(at.Siege, 0f).Value).ToArray(); float minX = pts.Min(p => p.x) - R, maxX = pts.Max(p => p.x) + R, minZ = pts.Min(p => p.z) - R, maxZ = pts.Max(p => p.z) + R;
            float demi = Mathf.Max(VueDeCarte.DEMI_MIN_KM, (maxX - minX) / (2f * Lot549.FORME * (x1 - x0) * 0.8f), (maxZ - minZ) / (2f * (y1 - y0) * 0.8f));
            carte.Vue.Centrer(new Vector2((minX + maxX) / 2f - ((x0 + x1) / 2f - 0.5f) * 2f * demi * Lot549.FORME, (minZ + maxZ) / 2f - ((y0 + y1) / 2f - 0.5f) * 2f * demi), demi); carte.Vue.Poser(camera, carte.transform, CarteDessinee.HAUTEUR_CAMERA);
        }
        static string Controler(Camera camera, Attendu at)
        {
            var dits = new List<string>(); Vector3 siege = Monde(at.Siege), haut = Monde(at.PHaut);
            foreach (var l in at.Lieux.Concat(new[] { ("du dû", at.Siege, at.Du) }))
            {
                bool du = l.Item1 == "du dû"; Vector3 a = du ? siege : Monde(l.Item2), b = du ? haut : siege; var f = carte.transform.Find(FlechesDeCarte.RACINE + "/Flèche " + l.Item1);
                if (l.Item3 <= 0 || Vector3.Distance(a, b) <= 2f * R) { if (f != null) throw Echec("flèche « " + l.Item1 + " » inattendue"); dits.Add(l.Item1 + " sans flèche"); continue; }
                var rendu = f != null ? f.GetComponent<MeshRenderer>() : null; if (rendu == null || !rendu.gameObject.activeInHierarchy || !rendu.enabled) throw Echec("flèche manquante : « Flèche " + l.Item1 + " »");
                var v = f.GetComponent<MeshFilter>().sharedMesh.vertices.Select(f.TransformPoint).ToArray(); Vector3 pied = (v[0] + v[3]) / 2f, u = (b - a).normalized; float w = Vector3.Distance(v[0], v[3]), attendue = FlechesDeCarte.Epaisseur(l.Item3);
                if (Vector3.Distance(pied, a + u * R) > 0.05f || Mathf.Abs(w - attendue) > 0.01f || !((Color32)rendu.sharedMaterial.color).Equals((Color32)(du ? FlechesDeCarte.VIOLET : FlechesDeCarte.ORANGE)) || Vector3.Angle(v[5] - pied, u) > 1f || !du && Mathf.Abs(Vector3.Distance(v[5], b) - R) > 0.05f) throw Echec("flèche " + l.Item1 + " : pied " + pied + ", largeur " + w + " pour " + attendue);
                foreach (var p in du ? new[] { pied, pied + u * 20f } : new[] { pied, (pied + v[5]) / 2f, v[5] }) { string sous = Sous(camera, p); if (sous != null) throw Echec("flèche " + l.Item1 + " " + sous); }
                dits.Add(l.Item1 + " " + l.Item3.ToString("0.##", Inv) + " kg, épaisseur " + attendue.ToString("0.###", Inv) + " attendue, " + w.ToString("0.###", Inv) + " observée");
            }
            var legende = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == "Légende des flèches"); if (legende == null || !legende.gameObject.activeInHierarchy || legende.preferredHeight > legende.rectTransform.rect.height + 1f) throw Echec("légende des flèches « " + Ligne(legende?.text) + " »"); Lot690.DansLeChamp(camera, legende);
            var panneau = toile.Cast<Transform>().OfType<RectTransform>().SingleOrDefault(t => t.name == FEUILLET && t.GetComponentInChildren<ScrollRect>(true) != null); if (panneau == null || !panneau.gameObject.activeInHierarchy) throw Echec("feuillet fermé");
            var texte = panneau.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text != null && t.text.Contains("Dû envoyé")) ?? throw Echec("feuillet sans comptes"); Lot690.DansLeChamp(camera, texte);
            var nom = carte.GetComponent<ReperesDeDepart.NomDuSiege>(); if (nom == null || nom.Nom == null || nom.Nom.text != SIEGE) throw Echec("siège non nommé"); string hors = Sous(camera, nom.Nom.GetComponent<Renderer>().bounds.center); if (hors != null) throw Echec("siège " + hors);
            return "flèches [" + string.Join("; ", dits) + "], dû vers " + at.Haut + " (" + at.PHaut.X.ToString("0", Inv) + ", " + at.PHaut.Y.ToString("0", Inv) + ")";
        }
        // Les panneaux qui prennent les clics et les deux légendes, en coordonnées de la photo.
        static IEnumerable<Rect> Caches(Camera camera)
        {
            foreach (var image in toile.GetComponentsInChildren<Image>(false)) { if (!image.gameObject.activeInHierarchy || !image.raycastTarget && image.name != "Fond de la légende" && image.name != "Fond des flèches") continue; var coins = new Vector3[4]; image.rectTransform.GetWorldCorners(coins); var p = coins.Select(c => camera.WorldToViewportPoint(c)).ToArray(); yield return Rect.MinMaxRect(p.Min(q => q.x), p.Min(q => q.y), p.Max(q => q.x), p.Max(q => q.y)); }
        }
        static string Sous(Camera camera, Vector3 monde) { Vector3 v = camera.WorldToViewportPoint(monde); if (v.z <= 0f || v.x < 0f || v.x > 1f || v.y < 0f || v.y > 1f) return "hors champ " + v.ToString("F2"); return Caches(camera).Any(c => c.Contains(v)) ? "sous un panneau ou une légende en " + v.ToString("F2") : null; }
        static Attendu Lire(int port, string id, long tick)
        {
            using (var monde = new ClientMonde(port, TimeSpan.FromSeconds(20))) using (var maisons = new ClientMaison(port, TimeSpan.FromSeconds(20))) using (var lieux = new ClientLieu(port, TimeSpan.FromSeconds(20)))
            {
                Lot690.ExigerMonde(monde.LireAvecMaison(), tick, id, "lecture indépendante"); var j = maisons.LireComptes(id); if (!j.Presente || j.Donnees.Maison.Siege.Nom != SIEGE || j.Donnees.Maison.Siege.Position == null || j.Donnees.Suzerain == null) throw Echec("comptes " + (j.Absence ?? "sans siège sur carte ou sans suzerain"));
                var s = maisons.LireComptes(j.Donnees.Suzerain); if (!s.Presente || s.Donnees.Maison.Siege.Position == null) throw Echec("suzerain " + j.Donnees.Suzerain + " : " + (s.Absence ?? "siège hors carte"));
                var siege = j.Donnees.Maison.Siege; var at = new Attendu { Siege = siege.Position.Value, Haut = s.Donnees.Maison.Siege.Nom, PHaut = s.Donnees.Maison.Siege.Position.Value, Preleve = j.Donnees.Flux.PreleveKg, Du = j.Donnees.Flux.DuEnvoyeKg };
                foreach (var t in j.Donnees.Maison.Lieux) if (!at.Cells.Contains(t.CellId)) at.Cells.Add(t.CellId);
                foreach (long cell in at.Cells)
                {
                    var lu = lieux.Lire(cell); if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Tick != tick) throw Echec("cellule " + N(cell) + " : " + (lu.Absence ?? lu.Lieu.AbsenceDesLieux ?? "tick " + N(lu.Lieu.Tick)));
                    foreach (var l in lu.Lieu.Lieux) if (l.Maitre == id && l.Flux != null) { if (cell == siege.CellId && l.Rang == siege.Rang) at.SurPlace = l.Flux.PreleveKg; else if (l.Position is PointCarte p) at.Lieux.Add((N(cell) + "-" + N(l.Rang), p, l.Flux.PreleveKg)); }
                }
                if (!at.Lieux.Any(l => l.kg > 0) || !(at.Du > 0) || at.SurPlace < 0) throw Echec("rien à montrer : " + at.Lieux.Count(l => l.kg > 0) + " lieux prélevés, dû " + at.Du.ToString(Inv) + ", sur place " + at.SurPlace.ToString(Inv));
                return at;
            }
        }
        static Button Bouton(string nom) { var t = racine.GetComponentsInChildren<Button>(true).Where(b => b.name == nom).ToArray(); if (t.Length != 1) throw Echec(t.Length + " boutons « " + nom + " »"); return t[0]; }
    }
}
