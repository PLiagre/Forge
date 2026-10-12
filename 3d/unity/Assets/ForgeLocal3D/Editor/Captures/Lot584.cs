using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Lot 584 : la capitale relancée à Biskra avec ses gestes. La capture tourne avec le service de `sim/` sur le port 8000,
    // à vitesse 0. On lit `/departs`, on y prend l'unique fiche dont le siège est Biskra, on choisit ce départ et un tick
    // l'applique. L'outil ouvre alors la cellule de Biskra, la preuve (#386) y joue ses trois gestes (route, parcelle,
    // scierie, puis sept ticks), et la ville est relevée. L'outil la rouvre comme au lancement, sans dépôt ni tick : la
    // ville redessinée doit être celle du relevé et du plan relu. Le panneau du lieu (cellule de la scène) est masqué ;
    // celui des gestes reste. La photo, vue de haut à 50°, montre la rue de terre, la parcelle à ses bornes et la scierie
    // à ses piquets. Le plan fixe, pris avant, montre le sable vierge.
    // Contre-épreuves : -forge584SansChoix omet le choix ; -forge584OublierRue remet le terrain à neuf après la réouverture ;
    // -forge584PanneauEtranger garde le panneau du lieu visible. Chacune doit faire échouer un contrôle ordinaire.
    static class Lot584
    {
        const string SIEGE = "Biskra";
        const string SANS_CHOIX = "-forge584SansChoix", OUBLIER_RUE = "-forge584OublierRue", PANNEAU_ETRANGER = "-forge584PanneauEtranger";
        // Un tick applique le choix ; la recette de la preuve fait trois ticks de dépôt, puis sept.
        const int TICKS_DU_CHOIX = 1, TICKS_DE_LA_RECETTE = 3 + 7;
        static readonly string[] TYPES = { "tracer_route", "decouper_parcelle", "poser_batiment" };
        const int DELAI_S = 60;
        const float INCLINAISON = 50f;
        const float ASPECT = 1600f / 900f;
        // Les bords de l'image que les points ne passent pas ; en bas, la place du panneau des gestes.
        const float MARGE = .06f, MARGE_BAS = .22f, TOLERANCE = .01f;
        const int IMAGES_DE_POSE = 10;

        static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);

        // Les lectures, hors du fil de l'éditeur, comme Lot362.
        static Dictionary<string, object> Lire(int port, string chemin)
        {
            string url = "http://127.0.0.1:" + port + chemin;
            var (statut, corps) = Task.Run(() =>
            {
                using (var http = new HttpClient { Timeout = TimeSpan.FromSeconds(DELAI_S) })
                using (var reponse = http.GetAsync(url).GetAwaiter().GetResult())
                    return ((int)reponse.StatusCode, Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()));
            }).GetAwaiter().GetResult();
            if (statut != 200)
                throw new InvalidOperationException("GET " + url + " a rendu " + statut + " : " + corps);
            return LecteurJson.LireObjet(corps);
        }

        static long Entier(Dictionary<string, object> objet, string cle, string ou) =>
            objet != null && objet.TryGetValue(cle, out object v) && v is double d && d >= 0 && d == Math.Floor(d) && d < 9007199254740992.0
                ? (long)d : throw new InvalidOperationException(ou + " : " + cle + " absent ou non entier");

        // L'unique fiche de `/departs` dont le siège est Biskra : (tick servi, seigneurie, cellule).
        static (long tick, long id, long cellule) Depart(int port)
        {
            var racine = Lire(port, "/departs");
            var fiches = (racine.TryGetValue("departs", out object brutes) ? brutes as List<object> : null)
                ?? throw new InvalidOperationException("/departs sans tableau departs");
            var biskra = fiches.OfType<Dictionary<string, object>>()
                .Where(f => f.TryGetValue("siege", out object s) && s is Dictionary<string, object> siege
                    && siege.TryGetValue("nom", out object nom) && nom as string == SIEGE).ToArray();
            if (biskra.Length != 1)
                throw new InvalidOperationException("/departs compte " + biskra.Length + " fiche(s) au siège " + SIEGE + " parmi " + fiches.Count + ", il en faut une");
            return (Entier(racine, "tick", "/departs"), Entier(biskra[0], "id", "fiche de " + SIEGE), Entier(biskra[0], "cell_id", "fiche de " + SIEGE));
        }

        static RecuIntention Deposer(int port, string intention) => Task.Run(() =>
        {
            using (var depot = new ClientIntention(port, TimeSpan.FromSeconds(DELAI_S)))
                return depot.Deposer(intention);
        }).GetAwaiter().GetResult();

        static string Hacher(string texte)
        {
            using (var sha = SHA256.Create())
                return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(texte)).Select(b => b.ToString("x2")));
        }

        static long[] Acceptees(IEnumerable<(long identifiant, DesertRoads.Resultat resultat)> essais) =>
            essais.Where(e => e.resultat.acceptee).Select(e => e.identifiant).ToArray();

        static string Etape(BatimentDuPlan b) =>
            LectureDuBatiment.Etape(b) switch { EtapeDuBatiment.Fini => "fini", EtapeDuBatiment.Murs => "murs", _ => "piquets" };

        static string Liste<T>(IEnumerable<T> v) => "[" + string.Join(", ", v) + "]";

        // Les toiles du panneau du lieu qu'on verrait : actives, avec un graphisme actif.
        static string[] ToilesVisibles(PanneauLieu panneau) => panneau.GetComponentsInChildren<Canvas>(true)
            .Where(c => c.isActiveAndEnabled && c.GetComponentsInChildren<Graphic>(false).Any(g => g.isActiveAndEnabled))
            .Select(c => c.name + " (" + string.Join(", ", c.GetComponentsInChildren<Graphic>(false).Where(g => g.isActiveAndEnabled).Select(g => g.name)) + ")")
            .ToArray();

        // La distance qui cadre tous les points en 1600 × 900 : dans le repère de la caméra posée au point visé, chaque
        // bord de l'image donne une distance minimale par point ; la plus grande les tient toutes.
        static float Distance(Vector3 vise, float cap, float champ, IEnumerable<Vector3> points)
        {
            var inverse = Quaternion.Inverse(Quaternion.Euler(INCLINAISON, cap, 0));
            float tanV = Mathf.Tan(champ * .5f * Mathf.Deg2Rad), tanH = tanV * ASPECT, d = 0;
            foreach (var p in points)
            {
                var q = inverse * (p - vise);
                d = Mathf.Max(d, Mathf.Abs(q.x) / (tanH * (1 - 2 * MARGE)) - q.z);
                d = Mathf.Max(d, q.y / (tanV * (1 - 2 * MARGE)) - q.z);
                d = Mathf.Max(d, -q.y / (tanV * (1 - 2 * MARGE_BAS)) - q.z);
            }
            return d;
        }

        // Les points hors du cadre 1600 × 900, vus de la caméra telle qu'elle est.
        static string[] HorsCadre(Camera camera, IEnumerable<(string nom, Vector3 p)> points)
        {
            float tanV = Mathf.Tan(camera.fieldOfView * .5f * Mathf.Deg2Rad), tanH = tanV * ASPECT;
            var inverse = Quaternion.Inverse(camera.transform.rotation);
            return points.Where(x =>
            {
                var q = inverse * (x.p - camera.transform.position);
                if (q.z <= 0) return true;
                float u = .5f + .5f * q.x / (q.z * tanH), v = .5f + .5f * q.y / (q.z * tanV);
                return u < MARGE - TOLERANCE || u > 1 - MARGE + TOLERANCE || v < MARGE_BAS - TOLERANCE || v > 1 - MARGE + TOLERANCE;
            }).Select(x => x.nom).ToArray();
        }

        [ScenarioDeCapture(584, "biskra-relancee")]
        static IEnumerator BiskraRelancee(Camera camera)
        {
            var outil = Object.FindFirstObjectByType<DesertRoadTool>();
            var ville = Object.FindFirstObjectByType<DesertCityCamera>();
            var panneau = Object.FindFirstObjectByType<PanneauLieu>();
            if (outil == null || ville == null || panneau == null)
                throw new InvalidOperationException("la scène n'a pas d'outil des routes, de DesertCityCamera ou de PanneauLieu");
            if (ville.GetComponent<Camera>() != camera)
                throw new InvalidOperationException("la DesertCityCamera n'est pas sur la caméra de la photo « " + camera.name + " » : le cadrage ne se vérifierait pas");
            outil.automatique = true;
            int port = outil.Port;

            // Le panneau du lieu dit la cellule de la scène, pas Biskra : ses lectures s'arrêtent, le composant et ses toiles
            // s'éteignent. Il doit être visible d'abord, sans quoi le contrôle des toiles ne pourrait pas échouer.
            int toiles = panneau.GetComponentsInChildren<Canvas>(true).Length;
            if (toiles == 0 || ToilesVisibles(panneau).Length == 0)
                throw new InvalidOperationException("le panneau du lieu n'a aucune toile visible avant le masquage (" + toiles + " toile(s))");
            if (!Drapeau(PANNEAU_ETRANGER))
            {
                panneau.Arreter();
                panneau.enabled = false;
                if (panneau.ObjetFoyers != null) panneau.ObjetFoyers.SetActive(false);
                foreach (var toile in panneau.GetComponentsInChildren<Canvas>(true))
                {
                    toile.enabled = false;
                    toile.gameObject.SetActive(false);
                }
            }

            // Le départ du Zab, lu dans la table servie ; un tick applique le choix.
            var (tickDepart, seigneurie, cellule) = Depart(port);
            string maison = "seigneurie-" + N(seigneurie);
            var defauts = new List<string>();
            RecuIntention choix = Drapeau(SANS_CHOIX) ? null
                : Deposer(port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + N(seigneurie) + "}");
            if (choix == null) defauts.Add("choix du départ " + N(seigneurie) + " sans reçu : aucun dépôt");
            else if (!choix.Acceptee) defauts.Add("le monde refuse le choix du départ " + N(seigneurie) + " : " + (choix.Presente ? choix.Erreur : choix.Absence));
            else if (choix.AppliqueeAuTick != tickDepart) defauts.Add("le choix est reçu au tick " + choix.AppliqueeAuTick + ", le service était au tick " + N(tickDepart));
            Lot362.Tick(port);
            var monde = Lire(port, "/monde");
            long tickChoisi = Entier(monde, "tick", "/monde");
            string tenue = monde.TryGetValue("maison_du_joueur", out object m) ? m as string ?? "?" : null;
            if (tickChoisi != tickDepart + TICKS_DU_CHOIX) defauts.Add("/monde au tick " + N(tickChoisi) + " après un tick depuis " + N(tickDepart));
            if (tenue != maison) defauts.Add("choix non appliqué : /monde au tick " + N(tickChoisi) + " dit maison_du_joueur " + (tenue ?? "absente") + ", attendue " + maison);
            Debug.Log("CAPTURE_584 départ : " + SIEGE + ", seigneurie " + N(seigneurie) + ", cellule " + N(cellule) + ", tick " + N(tickDepart)
                + ", reçu du choix " + (choix == null ? "aucun" : choix.Acceptee ? "au tick " + choix.AppliqueeAuTick : "refusé") + ", maison tenue " + (tenue ?? "aucune"));
            if (defauts.Count > 0)
                throw new InvalidOperationException(string.Join(" | ", defauts));

            // Biskra ouverte, les trois gestes de la preuve joués par l'outil du joueur.
            if (!outil.Ouvrir(cellule) || outil.Cellule != cellule)
                throw new InvalidOperationException("l'outil n'a pas ouvert la cellule " + N(cellule) + " : " + outil.Message);
            long[] ouvertes = Acceptees(outil.Ouverture);
            var preuve = DesertCityPreuve.JouerLesGestes(outil);
            if (preuve.defauts.Length > 0)
                throw new InvalidOperationException("les gestes de la preuve n'ont pas bâti Biskra : " + string.Join(" | ", preuve.defauts));
            var gestes = preuve.gestes;
            if (!gestes.Select(g => g.type).SequenceEqual(TYPES) || gestes.Any(g => g.identifiant < 0))
                throw new InvalidOperationException("gestes " + Liste(gestes.Select(g => g.type + " " + N(g.identifiant))) + " : il faut " + Liste(TYPES) + " identifiés");
            var recus = gestes.Select(g => g.apres_le_tick).ToArray();
            if (!recus.SequenceEqual(Enumerable.Range(0, TYPES.Length).Select(i => tickChoisi + i)))
                throw new InvalidOperationException("reçus des gestes aux ticks " + Liste(recus) + ", attendus dès le tick " + N(tickChoisi));
            var releve = preuve.ville;
            if (releve.tick != tickDepart + TICKS_DU_CHOIX + TICKS_DE_LA_RECETTE)
                throw new InvalidOperationException("ville relevée au tick " + N(releve.tick) + ", attendue au tick " + N(tickDepart + TICKS_DU_CHOIX + TICKS_DE_LA_RECETTE)
                    + " (" + N(tickDepart) + " + " + TICKS_DU_CHOIX + " + " + TICKS_DE_LA_RECETTE + ")");
            long rueId = gestes[0].identifiant, parcelleId = gestes[1].identifiant, scierieId = gestes[2].identifiant;

            // La réouverture, comme au lancement : Échap, puis Ouvrir, sans dépôt ni tick.
            outil.Annuler();
            if (!outil.Ouvrir())
                throw new InvalidOperationException("l'outil n'a pas rouvert Biskra : " + outil.Message);
            if (Drapeau(OUBLIER_RUE))
            {
                var g = DesertRoads.Lire(outil.roads.implantation);
                outil.roads.Preparer(g.parametres, g.graine);
            }

            // La ville rouverte contre le relevé conservé et le plan relu ; les étapes viennent du plan publié.
            var plan = Lot362.Lire(port, cellule);
            string t = "réouverture, tick " + N(plan.Tick) + " : ";
            var avant = ouvertes.Concat(releve.rues_posees).ToArray();
            var apres = Acceptees(outil.Ouverture);
            var rues = plan.Rues.Select(u => u.Identifiant).ToArray();
            var parcelles = outil.Parcelles.Select(p => N(p.identifiant) + " " + p.etat).ToArray();
            var parcellesPlan = plan.Parcelles.Select(p => N(p.Identifiant) + " " + (p.EnChantier ? "cordeau" : "bornes")).ToArray();
            var batiments = outil.Batiments.Select(b => N(b.identifiant) + " " + b.etat).ToArray();
            var batimentsPlan = plan.Batiments.Select(b => N(b.Identifiant) + " " + Etape(b)).ToArray();
            int piecesParcelles = outil.RacineParcelles ? outil.RacineParcelles.childCount : -1;
            int piecesBatiments = outil.RacineBatiments ? outil.RacineBatiments.childCount : -1;
            string empreinteRues = outil.roads.Empreintes().Tout, vide = Hacher("");

            if (plan.Tick != releve.tick) defauts.Add(t + "le plan relu n'est plus celui du relevé (tick " + N(releve.tick) + ")");
            if (rues.Length == 0 || parcellesPlan.Length == 0 || batimentsPlan.Length == 0)
                defauts.Add(t + "relevé vide : " + rues.Length + " rue(s), " + parcellesPlan.Length + " parcelle(s), " + batimentsPlan.Length + " bâtiment(s) au plan");
            if (!rues.SequenceEqual(releve.rues)) defauts.Add(t + "rues au plan " + Liste(rues) + " pour " + Liste(releve.rues) + " au relevé");
            if (!apres.SequenceEqual(avant) || !apres.SequenceEqual(rues))
                defauts.Add(t + "rues redessinées " + Liste(apres) + " pour " + Liste(avant) + " au relevé et " + Liste(rues) + " au plan");
            if (!parcelles.SequenceEqual(parcellesPlan) || !parcelles.SequenceEqual(releve.parcelles.Select(p => N(p.identifiant) + " " + p.etat)))
                defauts.Add(t + "parcelles redessinées " + Liste(parcelles) + " pour " + Liste(parcellesPlan) + " au plan");
            if (!batiments.SequenceEqual(batimentsPlan) || !batiments.SequenceEqual(releve.batiments.Select(b => N(b.identifiant) + " " + b.etat)))
                defauts.Add(t + "bâtiments redessinés " + Liste(batiments) + " pour " + Liste(batimentsPlan) + " au plan");
            if (piecesParcelles != plan.Parcelles.Count || piecesBatiments != plan.Batiments.Count
                || piecesParcelles != releve.pieces_parcelles || piecesBatiments != releve.pieces_batiments)
                defauts.Add(t + piecesParcelles + " et " + piecesBatiments + " pièce(s) (parcelles, bâtiments) pour " + releve.pieces_parcelles + " et "
                    + releve.pieces_batiments + " au relevé, " + plan.Parcelles.Count + " et " + plan.Batiments.Count + " au plan : un objet doublé ou perdu");
            bool memesEmpreintes = true;
            foreach (var (nom, a, b) in new[] { ("rues", empreinteRues, releve.empreinte_rues), ("parcelles", outil.EmpreinteParcelles, releve.empreinte_parcelles),
                ("bâtiments", outil.EmpreinteBatiments, releve.empreinte_batiments) })
            {
                if (string.IsNullOrEmpty(b) || b == vide) defauts.Add(t + "empreinte des " + nom + " vide au relevé");
                if (a != b) { memesEmpreintes = false; defauts.Add(t + "empreinte des " + nom + " " + a + " différente du relevé conservé " + b); }
            }

            // Les trois gestes, par les identifiants de leurs reçus.
            var rue = plan.Rues.FirstOrDefault(u => u.Identifiant == rueId);
            var parcelle = plan.Parcelles.FirstOrDefault(p => p.Identifiant == parcelleId);
            var scierie = plan.Batiments.FirstOrDefault(b => b.Identifiant == scierieId);
            if (rue == null || !outil.Ouverture.Any(e => e.identifiant == rueId && e.resultat.acceptee))
                defauts.Add(t + "la rue " + N(rueId) + (rue == null ? " n'est plus au plan" : " n'est pas redessinée"));
            if (parcelle == null || parcelle.EnChantier || !parcelles.Contains(N(parcelleId) + " bornes"))
                defauts.Add(t + "la parcelle " + N(parcelleId) + " n'est pas aux bornes au plan et au dessin : " + Liste(parcelles));
            if (scierie == null || scierie.Nature != "scierie" || scierie.Parcelle != parcelleId || Etape(scierie) != "piquets" || !batiments.Contains(N(scierieId) + " piquets"))
                defauts.Add(t + "le bâtiment " + N(scierieId) + " n'est pas une scierie aux piquets sur la parcelle " + N(parcelleId) + " : " + Liste(batiments));
            if (defauts.Count == 0 && (rue.Points.Count < 2 || parcelle.Contour.Count < 3))
                defauts.Add(t + "la rue ou la parcelle n'a pas assez de points pour le cadrage");
            Debug.Log("CAPTURE_584 " + SIEGE + ", cellule " + N(outil.Cellule) + ", tick " + N(plan.Tick) + " · reçus " + Liste(gestes.Select(g => g.type + " au tick " + N(g.apres_le_tick)))
                + " · rues " + Liste(apres) + " · parcelles " + Liste(parcelles) + " · bâtiments " + Liste(batiments) + " · pièces " + piecesParcelles + "/" + piecesBatiments
                + " · réouverture identique : " + (memesEmpreintes ? "oui" : "non") + " (empreintes rues, parcelles, bâtiments)");
            if (defauts.Count > 0)
                throw new InvalidOperationException(string.Join(" | ", defauts));

            // Vue de haut : la scierie au milieu, la rue entière et le contour de la parcelle dans le cadre, sa façade face à nous.
            var terrain = outil.roads.terrain;
            var points = rue.Points.Select((p, i) => ("rue " + i, Lot362.Monde(terrain, p.X, p.Y)))
                .Concat(parcelle.Contour.Select((p, i) => ("coin " + i, Lot362.Monde(terrain, p.X, p.Y)))).ToArray();
            var centre = Lot362.Monde(terrain, parcelle.Contour.Average(k => k.X), parcelle.Contour.Average(k => k.Y));
            double lacet = LectureDuBatiment.Poser(scierie).LacetDegres;
            float cap = double.IsNaN(lacet) ? ville.Cap : (float)lacet + 180f;
            ville.Poser(centre, cap, INCLINAISON, Distance(centre, cap, camera.fieldOfView, points.Select(x => x.Item2)));
            for (int i = 0; i < IMAGES_DE_POSE; i++)
                yield return null;

            var hors = HorsCadre(camera, points);
            var visibles = ToilesVisibles(panneau);
            Debug.Log("CAPTURE_584 caméra : distance " + ville.Distance.ToString("0.#", CultureInfo.InvariantCulture) + " m, inclinaison "
                + ville.Inclinaison.ToString("0", CultureInfo.InvariantCulture) + "°, " + (points.Length - hors.Length) + "/" + points.Length
                + " point(s) dans le cadre · toiles du lieu visibles : " + visibles.Length + "/" + toiles + " · panneau des gestes : " + outil.Message.Replace("\n", " | "));
            if (hors.Length > 0)
                defauts.Add("cadrage : " + Liste(hors) + " hors de l'image 1600 × 900 (distance " + ville.Distance.ToString("0.#", CultureInfo.InvariantCulture) + " m)");
            if (visibles.Length > 0)
                defauts.Add("toile du lieu encore visible après " + IMAGES_DE_POSE + " images : " + Liste(visibles));
            if (defauts.Count > 0)
                throw new InvalidOperationException(string.Join(" | ", defauts));
        }
    }
}
