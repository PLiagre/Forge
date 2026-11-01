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
    // Lot 657 : Mistra, prélèvement à 60 %, puis trente ticks (au plus si la chaîne part du tick 30). `-forge657RetirerLieu` retire un disque attendu.
    static class Lot657
    {
        const string SIEGE = "Mistra", RETIRER = "-forge657RetirerLieu", CONFIRMER = "Confirmer l\u2019ordre"; const int IMAGES = 10, TICKS = 30;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        static CarteDessinee carte; static Transform toile, racine; static CommandesMaison commandes; static string maison; static int port; static List<string> terres;
        static string N(long v) => v.ToString(Inv); static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static InvalidOperationException Echec(string c) => new InvalidOperationException(c);
        struct Pt { public long Cell, Rang, Partis, Arrives; public double X, Y; public string Maitre; public bool Rouge; }
        [ScenarioDeCapture(657, "lieux-et-departs")] static IEnumerator LieuxEtDeparts(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; port = carte.port; var cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("pas de cabinet");
            var vue = carte.GetComponent<LieuxDeCarte>() ?? throw Echec("la carte n'a pas de LieuxDeCarte"); if (carte.GetComponents<LieuxDeCarte>().Length != 1) throw Echec("vues multiples");
            var reperes = carte.GetComponent<ReperesDeDepart>() ?? throw Echec("pas de repères"); if (reperes.enabled) throw Echec("le prototype est resté actif");
            toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("toile inactive");
            commandes = carte.GetComponent<CommandesMaison>() ?? throw Echec("pas de commandes"); racine = toile.Find("Votre maison/Commandes de maison") ?? throw Echec("commandes introuvables");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            var partie = cabinet.Partie; var mistra = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray(); if (mistra.Length != 1) throw Echec(mistra.Length + " départs " + SIEGE);
            long tick = partie.Monde.Donnees.Monde.Tick; var choix = partie.Choisir(mistra[0].Id); for (var e = Lot690.Attendre(choix, "choix"); e.MoveNext();) yield return null;
            if (partie.Recu == null || !partie.Recu.Acceptee || partie.Recu.AppliqueeAuTick != tick) throw Echec("reçu du choix refusé");
            var un = Lot690.PousserTick(port); for (var e = Lot690.Attendre(un, "tick"); e.MoveNext();) yield return null; if (un.Result.statut != 200) throw Echec("tick " + un.Result.corps);
            for (var e = Lot690.Jusqua(() => Bouton("Prélèvement").interactable && partie.Maison?.Presente == true && partie.Maison.Donnees.Siege.Nom == SIEGE && partie.Monde.Donnees.MaisonDuJoueur == partie.Maison.Donnees.Id && partie.Monde.Donnees.Monde.Tick == tick + 1, () => "maison « " + (partie.Maison?.Absence ?? "") + " »"); e.MoveNext();) yield return null;
            maison = partie.Maison.Donnees.Id; Bouton("Prélèvement").onClick.Invoke(); yield return null;
            var curseur = racine.GetComponentInChildren<Slider>(true); if (curseur == null || !curseur.gameObject.activeInHierarchy) throw Echec("curseur invisible");
            curseur.value = 60; yield return null; var saisie = racine.GetComponentInChildren<InputField>(true);
            if (Math.Abs(curseur.value - 60f) > 0.01f || saisie == null || saisie.text != "60") throw Echec("curseur " + curseur.value);
            Bouton("Préparer").onClick.Invoke(); yield return null; Bouton(CONFIRMER).onClick.Invoke();
            for (var e = Lot690.Jusqua(() => commandes.Ordre.Recu != null && commandes.Ordre.Recu.Acceptee, () => "reçu « " + Ligne(commandes.MessageAffiche) + " »"); e.MoveNext();) yield return null;
            // Lancement nominal (tick 0) : trente ticks pleins, lecture et contrôle au tick 31. Lancée par la chaîne (tick 30), arrêt aux trois états : 10340 n'a plus d'autre maître sans perte nette dès le tick 53.
            long apres = commandes.Ordre.Recu.AppliqueeAuTick.Value; List<Pt> pts = null; int pousses = 0; bool nominal = tick == 0;
            for (; pousses < TICKS && (nominal || pts == null || Manque(pts) != null); pousses++) { var un1 = Lot690.PousserTick(port); for (var e = Lot690.Attendre(un1, "tick"); e.MoveNext();) yield return null; if (un1.Result.statut != 200) throw Echec("tick " + un1.Result.corps);
                long t = ++apres; if (nominal && pousses < TICKS - 1) continue; var lu = Task.Run(() => Lire(port, maison, t)); for (var e = Lot690.Attendre(lu, "référence"); e.MoveNext();) yield return null; (pts, terres) = lu.Result; }
            if (nominal && apres != TICKS + 1) throw Echec("relecture au tick " + N(apres) + ", attendu " + N(TICKS + 1)); if (pts.Count == 0) throw Echec("aucun lieu servi"); if (Manque(pts) != null) throw Echec(Manque(pts) + " après " + pousses + " ticks");
            for (var e = Lot690.Jusqua(() => Pret(vue, pts, apres), () => "légende « " + Ligne(vue.TexteLegende) + " » disques " + Disques()); e.MoveNext();) yield return null;
            Cadrer(pts); yield return null; Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f);
            var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases(); Controler(camera, pts, apres);
            if (Environment.GetCommandLineArgs().Contains(RETIRER)) { var d = Disque(pts[0].Cell, pts[0].Rang); if (d != null) d.gameObject.SetActive(false); }
            for (int i = 0; i < IMAGES; i++) yield return null; Controler(camera, pts, apres);
            Debug.Log("CAPTURE_657 maison " + maison + ", ticks " + N(apres) + ", couples attendus " + pts.Count + ", observés " + Disques() + ", rouges " + pts.Count(p => p.Rouge) + " [" + string.Join(", ", pts.Where(p => p.Rouge).Select(p => N(p.Cell) + "-" + N(p.Rang) + " partis " + N(p.Partis) + " arrivées " + N(p.Arrives))) + "]");
        }
        static bool Pret(LieuxDeCarte vue, List<Pt> pts, long tick) { string t = vue.TexteLegende; return t != null && Disques() == pts.Count && terres.All(t.Contains); }
        static void Cadrer(List<Pt> pts)
        {
            if (carte.Vue == null) throw Echec("la carte n'a pas de vue");
            float minX = float.MaxValue, maxX = float.MinValue, minZ = float.MaxValue, maxZ = float.MinValue;
            foreach (var p in pts) { Vector3 l = carte.PositionSurLaCarte(new PointCarte(p.X, p.Y), ReperesDeDepart.HAUTEUR_LIEU).Value; minX = Mathf.Min(minX, l.x); maxX = Mathf.Max(maxX, l.x); minZ = Mathf.Min(minZ, l.z); maxZ = Mathf.Max(maxZ, l.z); }
            float cx = (minX + maxX) / 2f, cz = (minZ + maxZ) / 2f, aspect = Mathf.Max(carte.Vue.Aspect, 1e-4f), rayon = ReperesDeDepart.DIAMETRE_BORD_KM / 2f;
            float demi = Mathf.Max(Mathf.Max(Mathf.Abs(maxZ - cz), Mathf.Abs(minZ - cz)) + rayon, (Mathf.Max(Mathf.Abs(maxX - cx), Mathf.Abs(minX - cx)) + rayon) / aspect);
            float vu = Mathf.Max(VueDeCarte.DEMI_MIN_KM, demi * VueDeCarte.MARGE * 4f); carte.Vue.Centrer(new Vector2(cx, cz - vu * 0.1f), vu); carte.Vue.Poser(carte.camera, carte.transform, CarteDessinee.HAUTEUR_CAMERA);
        }
        static void Controler(Camera camera, List<Pt> pts, long tick)
        {
            foreach (var p in pts) { string couple = N(p.Cell) + "-" + N(p.Rang); var disque = Disque(p.Cell, p.Rang); var rendu = disque != null ? disque.GetComponent<MeshRenderer>() : null; if (disque == null || !disque.gameObject.activeInHierarchy || rendu == null || !rendu.enabled) throw Echec("couple manquant " + couple); Vector3 attendu = carte.transform.TransformPoint(carte.PositionSurLaCarte(new PointCarte(p.X, p.Y), ReperesDeDepart.HAUTEUR_LIEU).Value); Color couleur = p.Rouge ? LieuxDeCarte.ROUGE : p.Maitre == maison ? ReperesDeDepart.COULEUR_JOUEUR : LieuxDeCarte.CouleurDuMaitre(p.Maitre); if ((disque.position - attendu).sqrMagnitude > 1e-4f || !((Color32)rendu.sharedMaterial.color).Equals((Color32)couleur)) throw Echec("couple " + couple + " mal placé ou mal coloré"); string panneau = SousPanneau(camera, disque.position); if (panneau != null) throw Echec("couple " + couple + " " + panneau); }
            if (Disques() != pts.Count) throw Echec("disques " + Disques() + " pour " + pts.Count);
            var legende = toile.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == "Légende des lieux");
            if (legende == null || !legende.text.Contains(LieuxDeCarte.ENTETE) || legende.text.Contains("même instant") || legende.preferredHeight > legende.rectTransform.rect.height + 1f) throw Echec("légende « " + Ligne(legende != null ? legende.text : null) + " »");
            foreach (string terre in terres) if (!legende.text.Contains(terre)) throw Echec("terre absente « " + Ligne(terre) + " »");
            string mot = TexteDuMonde.Interdit(legende.text, maison) ?? TexteDuMonde.SansUnite(legende.text); if (mot != null) throw Echec("légende des lieux : « " + mot + " » dans « " + Ligne(legende.text) + " »");
            Lot690.DansLeChamp(camera, legende); var nom = carte.GetComponent<ReperesDeDepart.NomDuSiege>();
            if (nom == null || nom.Nom == null || nom.Nom.text != SIEGE) throw Echec("siège non nommé");
            string hors = SousPanneau(camera, nom.Nom.GetComponent<Renderer>().bounds.center); if (hors != null) throw Echec("siège " + hors);
        }
        static string SousPanneau(Camera camera, Vector3 monde)
        {
            Vector3 v = camera.WorldToViewportPoint(monde); if (v.z <= 0f || v.x < 0f || v.x > 1f || v.y < 0f || v.y > 1f) return "hors champ " + v.ToString("F2");
            foreach (var image in toile.GetComponentsInChildren<Image>(false)) { if (!image.raycastTarget || !image.gameObject.activeInHierarchy) continue; var coins = new Vector3[4]; image.rectTransform.GetWorldCorners(coins); float x0 = 1f, x1 = 0f, y0 = 1f, y1 = 0f; for (int i = 0; i < 4; i++) { Vector3 p = camera.WorldToViewportPoint(coins[i]); x0 = Mathf.Min(x0, p.x); x1 = Mathf.Max(x1, p.x); y0 = Mathf.Min(y0, p.y); y1 = Mathf.Max(y1, p.y); } if (v.x >= x0 && v.x <= x1 && v.y >= y0 && v.y <= y1) return "sous « " + image.name + " »"; }
            return null;
        }
        static string Manque(List<Pt> pts) { bool b = pts.Any(p => !p.Rouge && p.Maitre == maison), r = pts.Any(p => p.Rouge), a = pts.Any(p => !p.Rouge && p.Maitre != maison); return b && r && a ? null : "états manquants : blanc " + b + ", rouge " + r + ", autre maître " + a; }
        // Les points des lieux, et la ligne de chaque terre telle que la légende doit la dire : son bourg servi, la date servie.
        static (List<Pt>, List<string>) Lire(int port, string id, long tick)
        {
            using (var monde = new ClientMonde(port, TimeSpan.FromSeconds(20))) using (var maisons = new ClientMaison(port, ClientDeparts.DelaiMinimal)) using (var lieux = new ClientLieu(port, TimeSpan.FromSeconds(20)))
            {
                var m = monde.LireAvecMaison(); if (!m.Presente || m.Donnees.MaisonDuJoueur != id || m.Donnees.Monde.Tick != tick) throw Echec("monde " + (m.Presente ? N(m.Donnees.Monde.Tick) + " " + m.Donnees.MaisonDuJoueur : m.Absence));
                var h = maisons.Lire(id); if (!h.Presente || h.Donnees.Siege.Nom != SIEGE) throw Echec(h.Presente ? h.Donnees.Siege.Nom : h.Absence);
                var cells = new List<long>(); foreach (var t in h.Donnees.Lieux) if (!cells.Contains(t.CellId)) cells.Add(t.CellId); var pts = new List<Pt>(); var lignes = new List<string>();
                foreach (long cell in cells)
                {
                    var lu = lieux.Lire(cell); if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Tick != tick) throw Echec(lu.Presente ? "cellule " + N(cell) + " " + lu.Lieu.AbsenceDesLieux : lu.Absence);
                    lignes.Add("\n" + (lu.Lieu.Bourg?.Nom ?? throw Echec("bourg sans nom servi : cellule " + N(cell))) + " · relevé au " + TexteDuMonde.Date(new DateDuMonde(lu.Lieu.Annee, lu.Lieu.JourDeLAnnee)));
                    foreach (var lieu in lu.Lieu.Lieux) if (lieu.Position is PointCarte point && lieu.Maitre != null) pts.Add(new Pt { Cell = cell, Rang = lieu.Rang, X = point.X, Y = point.Y, Maitre = lieu.Maitre, Partis = lieu.Flux != null ? lieu.Flux.PartisPersonnes : 0, Arrives = lieu.Flux != null ? lieu.Flux.ArrivesPersonnes : 0, Rouge = lieu.Flux != null && lieu.Flux.PartisPersonnes > lieu.Flux.ArrivesPersonnes });
                }
                return (pts, lignes);
            }
        }
        static Transform Disque(long cell, long rang) => carte.transform.Find(LieuxDeCarte.RACINE + "/" + ReperesDeDepart.NomDuLieu(cell, rang) + "/Disque");
        static int Disques() { var r = carte.transform.Find(LieuxDeCarte.RACINE); if (r == null) return 0; int n = 0; foreach (Transform e in r) { var d = e.Find("Disque"); if (d != null && d.gameObject.activeInHierarchy) n++; } return n; }
        static Button Bouton(string nom) { var t = racine.GetComponentsInChildren<Button>(true).Where(b => b.name == nom).ToArray(); if (t.Length != 1) throw Echec(t.Length + " boutons « " + nom + " »"); return t[0]; }
    }
}
