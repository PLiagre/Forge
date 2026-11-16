using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using Object = UnityEngine.Object;

namespace ForgeLocal3D.Captures
{
    // Sur le service de la capture, Biskra (le Zab) : le joueur monte sa part de grain au plus haut, trace la route de l'est,
    // fait découper une parcelle, attend que le grenier paie la caserne, puis l'outil de la ville forme et dépose la caserne
    // par un clic sur la parcelle. Trois images la montrent aux piquets, aux murs, puis finie, la caméra immobile. Chaque
    // relevé parcourt la scène et le plan servi par le monde : la pièce posée sous RacineBatiments, son prefab dans le kit,
    // la ligne du panneau, l'étape et le travail du plan. Le tick n'est jamais écrit : c'est celui que le service sert.
    // Si le grenier ne paie pas, le refus du monde, mot pour mot, fait échouer le scénario. Rapport : `caserne.json`.
    static class ScenarioCaserne
    {
        const string Rapport = "caserne.json", Siege = "Biskra", Nature = "caserne", Piece = "Caserne ", RacineDesPieces = "Bâtiments du plan";
        const double PartDuGrain = 0.6;
        const int TicksParcelle = 12, TicksGrenier = 15, TicksChantier = 40, Images = 10;
        // La route de l'est, en mètres du bourg, et la parcelle qu'on y découpe, à sa gauche : à 2 m du départ, 10 m de façade, 20 m de fond.
        // Le tracé tient à l'est des maisons de 1400 (x ≤ 69) et sur un relief où la pente reste sous la limite des routes.
        static readonly (double x, double y)[] Route = { (72, -40), (94, -40) };
        const double DebutM = 2, FacadeM = 10, ProfondeurM = 20, LargeurRoute = 4, Tolerance = 0.5;
        const string Cote = "gauche";
        // La parcelle que le service dessine : au nord de la route (y croissant), à une demi-largeur de chaussée de son axe. Le point cliqué est son centre.
        static readonly double X0 = Route[0].x + DebutM, X1 = X0 + FacadeM, Y0 = Route[0].y + LargeurRoute / 2, Y1 = Y0 + ProfondeurM, CentreX = (X0 + X1) / 2, CentreY = (Y0 + Y1) / 2;
        // La caméra : de trois quarts, depuis la rue, la façade de la caserne et la route dans l'image.
        // Les panneaux couvrent la gauche de l'image : l'ensemble se centre à droite d'eux.
        const float CapDeVue = 160f, InclinaisonDeVue = 35f, HauteurDeLaTour = 14f;
        static readonly Vector2 CentreDeLImage = new(0.68f, 0.5f);

        static readonly List<string> images = new();
        static readonly List<string> devis = new();
        static DesertRoadTool outil;
        static string rapport, etape = "aucune", maison, contourParcelle = "[]", routePosee;
        static long cellule = -1, tickDepart = -1, rue = -1, parcelle = -1;
        static RecuIntention recu;
        static (Vector3 vise, float distance)? cadre;
        static double debutScenario;

        static Exception Faux(string m) => new InvalidOperationException(m);

        [ScenarioDeCapture("caserne", "1-caserne-aux-piquets")]
        static IEnumerator AuxPiquets(Camera camera) { debutScenario = Time.realtimeSinceStartupAsDouble; return Derouler(Piquets(camera)); }
        [ScenarioDeCapture("caserne", "2-caserne-aux-murs")]
        static IEnumerator AuxMurs(Camera camera) { debutScenario = Time.realtimeSinceStartupAsDouble; return Derouler(Murs(camera)); }
        [ScenarioDeCapture("caserne", "3-caserne-finie")]
        static IEnumerator Finie(Camera camera) { debutScenario = Time.realtimeSinceStartupAsDouble; return Derouler(Acheve(camera)); }

        // Toute exception inscrit « étape : message » au rapport, puis fait échouer la capture.
        static IEnumerator Derouler(IEnumerator corps)
        {
            while (true)
            {
                bool suite;
                try { suite = corps.MoveNext(); }
                catch (Exception e) { if (rapport != null) Ecrire(etape + " : " + e.GetBaseException().Message); throw; }
                if (!suite) yield break;
                yield return null;
            }
        }

        // L'étape 1 : le départ, le grain, la route, la parcelle, le grenier, le clic ; puis la caserne aux piquets.
        static IEnumerator Piquets(Camera camera)
        {
            images.Clear(); devis.Clear(); outil = null; cellule = tickDepart = rue = parcelle = -1; contourParcelle = "[]"; routePosee = null; recu = null; cadre = null;
            maison = null; etape = "ouverture"; rapport = Path.Combine(Capture.DossierDesCaptures, Rapport); Ecrire("session interrompue avant l'image 1");
            outil = Object.FindFirstObjectByType<DesertRoadTool>() ?? throw Faux("pas d'outil");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            var lieu = Object.FindFirstObjectByType<PanneauLieu>() ?? throw Faux("pas de panneau du lieu");
            outil.automatique = ville.automatique = true; if (ville.Marcheur) ville.Marcheur.automatic = true;
            var lus = Task.Run(() => { using (var d = new ClientDeparts(outil.Port, ClientDeparts.DelaiMinimal)) return d.Lire(); });
            while (!lus.IsCompleted) yield return null;
            if (lus.IsFaulted || !lus.Result.Presente) throw Faux(lus.IsFaulted ? lus.Exception.GetBaseException().Message : lus.Result.Absence);
            var zab = lus.Result.Donnees.Fiches.Where(f => f.Siege.Nom == Siege).ToArray();
            if (zab.Length != 1) throw Faux(zab.Length + " sièges " + Siege);
            long c = zab[0].CellId; cellule = c; maison = "seigneurie-" + zab[0].Id;
            string geste = "\"maison\":\"" + maison + "\",\"cell\":" + L(c);

            // Le choix de départ, un tick : le monde sert alors la maison du joueur et ses gestes de bâtisseur.
            etape = "départ"; var port = outil.Port;
            GestesDeCapture.Deposer(port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + zab[0].Id + "}"); GestesDeCapture.Tick(port);
            tickDepart = GestesDeCapture.Lire(port, c).Tick; Debug.Log("CAPTURE_CASERNE départ servi au tick " + L(tickDepart));
            yield return null;

            // Le grain : la part du joueur au plus haut, puis la route de l'est (l'ouest est refusé par le relief).
            etape = "grain et route";
            GestesDeCapture.Deposer(port, "{\"type\":\"fixer_part\",\"maison\":\"" + maison + "\",\"part\":" + N(PartDuGrain) + "}");
            GestesDeCapture.Deposer(port, "{\"type\":\"tracer_route\"," + geste + ",\"points\":[" + string.Join(",", Route.Select(p => P(p.x, p.y))) + "],\"largeur_m\":" + N(LargeurRoute) + "}");
            GestesDeCapture.Tick(port);
            var plan = GestesDeCapture.Lire(port, c);
            var route = plan.Rues.FirstOrDefault(u => u.Points.Count == Route.Length && Enumerable.Range(0, Route.Length).All(i => Math.Abs(u.Points[i].X - Route[i].x) < 1e-6 && Math.Abs(u.Points[i].Y - Route[i].y) < 1e-6))
                ?? throw Faux("la route de l'est n'est pas au plan du tick " + L(plan.Tick));
            rue = route.Identifiant; yield return null;

            // La parcelle, puis les ticks qui l'achèvent.
            etape = "parcelle";
            var avant = new HashSet<long>(plan.Parcelles.Select(p => p.Identifiant));
            GestesDeCapture.Deposer(port, "{\"type\":\"decouper_parcelle\"," + geste + ",\"rue\":" + L(rue) + ",\"segment\":0,\"debut_m\":" + N(DebutM) + ",\"facade_m\":" + N(FacadeM)
                + ",\"profondeur_m\":" + N(ProfondeurM) + ",\"cote\":\"" + Cote + "\"}");
            for (int k = 0; ; k++)
            {
                GestesDeCapture.Tick(port); plan = GestesDeCapture.Lire(port, c);
                var neuves = plan.Parcelles.Where(p => !avant.Contains(p.Identifiant)).ToArray();
                if (neuves.Length > 1) throw Faux(neuves.Length + " parcelles neuves au plan du tick " + L(plan.Tick));
                if (neuves.Length == 1 && !neuves[0].EnChantier) { parcelle = neuves[0].Identifiant; contourParcelle = "[" + string.Join(",", neuves[0].Contour.Select(q => P(q.X, q.Y))) + "]"; break; }
                if (k >= TicksParcelle) throw Faux("parcelle inachevée après " + TicksParcelle + " ticks, au tick " + L(plan.Tick));
                yield return null;
            }
            var contour = plan.Parcelles.First(p => p.Identifiant == parcelle).Contour;
            bool Pres(double a, double b) => Math.Abs(a - b) < Tolerance;
            if (!(Pres(contour.Min(q => q.X), X0) && Pres(contour.Max(q => q.X), X1) && Pres(contour.Min(q => q.Y), Y0) && Pres(contour.Max(q => q.Y), Y1)))
                throw Faux("la parcelle " + L(parcelle) + " n'est pas à (" + N(X0) + " ; " + N(Y0) + ")–(" + N(X1) + " ; " + N(Y1) + ") : " + contourParcelle);

            // Le grenier : le devis du monde, un tick à la fois, jusqu'à ce qu'il paie la caserne.
            etape = "grenier";
            for (int k = 0; ; k++)
            {
                var ordres = Ordres(port);
                if (!ordres.Presente) throw Faux("devis absent : " + ordres.Absence);
                var levee = ordres.Donnees.Levee; var bat = levee.Batiment ?? throw Faux("la capitale est hors de la carte : pas de devis de la caserne");
                devis.Add("{\"tick\":" + L(ordres.Donnees.Tick) + ",\"refus\":" + Q(bat.Refus) + ",\"grain_libre_kg\":" + N(levee.GrainLibreKg) + ",\"cout_kg\":" + N(bat.CoutKg)
                    + ",\"journees\":" + L(bat.Journees) + ",\"bras_par_jour\":" + L(bat.BrasParJour) + "}");
                if (bat.Refus == null) break;
                if (k >= TicksGrenier) throw Faux("le grenier ne paie pas la caserne après " + TicksGrenier + " ticks, au tick " + L(ordres.Donnees.Tick) + " : " + bat.Refus);
                GestesDeCapture.Tick(port); yield return null;
            }

            // La ville, l'outil en mode caserne, un clic au centre de la parcelle, de haut, sur une image de la taille de la photo.
            etape = "ouverture de " + Siege; if (!outil.Ouvrir(c)) throw Faux(outil.Message); lieu.Ouvrir(c);
            // La route est au plan ; la 3D peut la refuser (pente du relief) : le rapport dit ce que la photo en montre.
            var posee = outil.Ouverture.FirstOrDefault(o => o.identifiant == rue);
            routePosee = posee.resultat == null ? "jamais essayée" : posee.resultat.acceptee ? "posée" : posee.resultat.message;
            Debug.Log("CAPTURE_CASERNE route " + L(rue) + " : " + routePosee);
            etape = "clic"; var t = outil.roads.terrain; outil.EntrerCaserne();
            if (!outil.ModeCaserne) throw Faux("l'outil n'est pas en mode caserne : " + outil.Message);
            var rt = new RenderTexture(1600, 900, 24); camera.targetTexture = rt;
            try
            {
                var m = GestesDeCapture.Monde(t, CentreX, CentreY); ville.Poser(m, ville.Cap, 85f, 60f);
                if (!outil.Clic(camera.WorldToScreenPoint(m))) throw Faux("clic en " + P(CentreX, CentreY) + " refusé : " + outil.Message);
            }
            finally { camera.targetTexture = null; rt.Release(); Object.DestroyImmediate(rt); }
            recu = outil.Recu;
            if (outil.PoseCaserne == null || !outil.PoseCaserne.Presente || outil.PoseCaserne.Parcelle != parcelle)
                throw Faux("caserne désignée sur la parcelle " + (outil.PoseCaserne == null ? "aucune" : outil.PoseCaserne.Presente ? L(outil.PoseCaserne.Parcelle) : outil.PoseCaserne.Absence) + " au lieu de " + L(parcelle));
            if (recu == null || !recu.Acceptee) throw Faux("caserne refusée par le monde : " + (recu == null ? "pas de reçu" : recu.Presente ? recu.Erreur : recu.Absence) + " · " + outil.Message);

            // Un tick : le chantier s'ouvre, l'outil le dessine.
            etape = "tick du dépôt"; GestesDeCapture.Tick(port);
            if (!outil.Attendre()) throw Faux("Attendre faux après le tick : " + Panneau());
            Relever("piquets", camera); yield return null;

            // Le cadrage, cherché sur la parcelle, la route devant elle et la tour de la caserne.
            etape = "cadrage"; camera.aspect = 1600f / 900f;
            var vise = GestesDeCapture.Monde(t, CentreX, CentreY - 6);
            var cibles = contour.Select(q => GestesDeCapture.Monde(t, q.X, q.Y)).Concat(contour.Select(q => GestesDeCapture.Monde(t, q.X, q.Y) + Vector3.up * HauteurDeLaTour))
                .Concat(new[] { X0 - 2, X1 + 6 }.SelectMany(x => new[] { Route[0].y - LargeurRoute / 2, Route[0].y + LargeurRoute / 2 }.Select(y => GestesDeCapture.Monde(t, x, y)))).ToArray();
            // À chaque distance, la vise glisse pour que l'ensemble se centre sur la zone libre de l'image (à droite des panneaux).
            for (float d = 12f; d <= DesertCityCamera.DistanceMax && cadre == null; d *= 1.03f)
            {
                var v0 = vise;
                for (int pas = 0; pas < 5; pas++)
                {
                    ville.Poser(v0, CapDeVue, InclinaisonDeVue, d);
                    var q = cibles.Select(x => camera.WorldToViewportPoint(x)).ToArray();
                    float cx = (q.Min(a => a.x) + q.Max(a => a.x)) / 2, cy = (q.Min(a => a.y) + q.Max(a => a.y)) / 2;
                    float demi = d * Mathf.Tan(camera.fieldOfView * Mathf.Deg2Rad / 2);
                    var plat = Vector3.ProjectOnPlane(camera.transform.forward, Vector3.up).normalized;
                    v0 += camera.transform.right * ((cx - CentreDeLImage.x) * 2 * demi * camera.aspect) + plat * ((cy - CentreDeLImage.y) * 2 * demi / Mathf.Sin(InclinaisonDeVue * Mathf.Deg2Rad));
                }
                ville.Poser(v0, CapDeVue, InclinaisonDeVue, d);
                if (cibles.All(v => Dans(camera, v))) cadre = (v0, d);
            }
            if (cadre == null) throw Faux("cadrage impossible, caméra " + camera.transform.position);
            Cadrer(camera, ville); for (int k = 0; k < Images; k++) yield return null;
            Image("1-caserne-aux-piquets");
        }

        // L'étape 2 : des ticks jusqu'à l'étape des murs, et pas au-delà.
        static IEnumerator Murs(Camera camera)
        {
            Reprendre("1-caserne-aux-piquets");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            etape = "chantier";
            for (int k = 0; ; k++)
            {
                var e = EtapeDuPlan(out var b, out long tick);
                if (e == EtapeDuBatiment.Murs) break;
                if (e == EtapeDuBatiment.Fini || !b.EnChantier) throw Faux("la caserne a passé l'étape des murs sans qu'on la voie, au tick " + L(tick) + " : " + b.TravailFourni + "/" + b.TravailRequis);
                if (k >= TicksChantier) throw Faux("caserne encore aux piquets après " + TicksChantier + " ticks : fourni " + b.TravailFourni + "/" + b.TravailRequis);
                GestesDeCapture.Tick(outil.Port); yield return null;
            }
            if (!outil.Rafraichir()) throw Faux("rafraîchir : " + outil.Message);
            Relever("murs", camera); Cadrer(camera, ville);
            for (int k = 0; k < Images; k++) yield return null;
            Image("2-caserne-aux-murs");
        }

        // L'étape 3 : des ticks jusqu'à l'achèvement, puis le devis : la levée s'est ouverte.
        static IEnumerator Acheve(Camera camera)
        {
            Reprendre("2-caserne-aux-murs");
            var ville = camera.GetComponent<DesertCityCamera>() ?? throw Faux("pas de caméra de ville");
            etape = "chantier";
            for (int k = 0; ; k++)
            {
                var e = EtapeDuPlan(out var b, out _);
                if (e == EtapeDuBatiment.Fini) break;
                if (k >= TicksChantier) throw Faux("caserne inachevée après " + TicksChantier + " ticks : fourni " + b.TravailFourni + "/" + b.TravailRequis);
                GestesDeCapture.Tick(outil.Port); yield return null;
            }
            if (!outil.Rafraichir()) throw Faux("rafraîchir : " + outil.Message);
            Relever("fini", camera); Cadrer(camera, ville);
            etape = "levée";
            var ordres = Ordres(outil.Port);
            if (!ordres.Presente) throw Faux("devis absent : " + ordres.Absence);
            var lev = ordres.Donnees.Levee;
            devis.Add("{\"tick\":" + L(ordres.Donnees.Tick) + ",\"levee_refus\":" + Q(lev.Refus) + ",\"grain_libre_kg\":" + N(lev.GrainLibreKg) + "}");
            if (lev.Refus != null) throw Faux("la caserne est finie mais la levée reste fermée : " + lev.Refus);
            for (int k = 0; k < Images; k++) yield return null;
            Image("3-caserne-finie");
            Debug.Log("CAPTURE_CASERNE " + Ecrire(null));
        }

        static void Reprendre(string precedent)
        {
            if (outil == null || cadre == null || images.Count == 0 || parcelle < 0) throw Faux("le scénario « " + precedent + " » n'a pas joué");
            if (!outil) throw Faux("l'outil de la ville a disparu après « " + precedent + " »");
        }

        static void Cadrer(Camera camera, DesertCityCamera ville) { camera.aspect = 1600f / 900f; ville.Poser(cadre.Value.vise, CapDeVue, InclinaisonDeVue, cadre.Value.distance); }

        // La caserne du plan servi, à la parcelle du scénario : son étape, son tick.
        static EtapeDuBatiment EtapeDuPlan(out BatimentDeProvinceDuPlan b, out long tick)
        {
            var plan = GestesDeCapture.Lire(outil.Port, cellule); tick = plan.Tick;
            var casernes = plan.BatimentsDeProvince.Where(x => x.Nature == Nature).ToArray();
            if (casernes.Length != 1 || casernes[0].Parcelle != parcelle) throw Faux(casernes.Length + " caserne(s) au plan du tick " + L(plan.Tick) + (casernes.Length == 1 ? ", sur la parcelle " + L(casernes[0].Parcelle) : ""));
            b = casernes[0]; return LectureDuBatiment.Etape(b);
        }

        // Le relevé après un dessin : l'étape du plan, la pièce de la scène, son prefab dans le kit, la ligne du panneau.
        static void Relever(string attendue, Camera camera)
        {
            etape = "relevé « " + attendue + " »";
            var plan = GestesDeCapture.Lire(outil.Port, cellule);
            var casernes = plan.BatimentsDeProvince.Where(x => x.Nature == Nature).ToArray();
            if (casernes.Length != 1 || casernes[0].Parcelle != parcelle) throw Faux(casernes.Length + " caserne(s) au plan du tick " + L(plan.Tick));
            var b = casernes[0]; var et = LectureDuBatiment.Etape(b);
            if (et.ToString().ToLowerInvariant() != attendue) throw Faux("étape du plan au tick " + L(plan.Tick) + " : " + et + " au lieu de " + attendue + " (" + b.TravailFourni + "/" + b.TravailRequis + ")");
            var dessin = outil.BatimentsDeProvince.Where(x => x.identifiant == b.Identifiant).ToArray();
            if (dessin.Length != 1 || dessin[0].etat != attendue) throw Faux("dessin de l'outil : " + string.Join(" ; ", dessin.Select(x => x.etat + " " + x.message)) + " au lieu de " + attendue);

            // La pièce : un Transform actif « Caserne <identifiant> » sous RacineBatiments, et une seule.
            var racine = outil.RacineBatiments ?? throw Faux("l'outil n'a pas de racine des bâtiments");
            if (racine.name != RacineDesPieces) throw Faux("racine des bâtiments « " + racine.name + " »");
            string nom = Piece + L(b.Identifiant);
            var pieces = Object.FindObjectsByType<Transform>(FindObjectsInactive.Exclude, FindObjectsSortMode.None).Where(x => x.parent == racine && x.name.StartsWith(Piece, StringComparison.Ordinal)).ToArray();
            if (pieces.Length != 1 || pieces[0].name != nom || !pieces[0].gameObject.activeInHierarchy) throw Faux("pièces de caserne sous la racine : " + string.Join(" ; ", pieces.Select(x => x.name)) + " au lieu de « " + nom + " »");
            var piece = pieces[0];
            var kit = KitDesBatiments.Charger() ?? throw Faux("pas de kit des bâtiments");
            var du = kit.Piece(Nature, et); if (!du.Presente) throw Faux("le kit n'a pas de pièce pour " + et + " : " + du.Absence);
            string prefab = du.Prefab.name, attenduPrefab = attendue == "fini" ? "caserne" : "chantier_caserne_" + attendue;
            if (prefab != attenduPrefab) throw Faux("le kit sert « " + prefab + " » pour l'étape " + attendue + " au lieu de « " + attenduPrefab + " »");
            // L'instance est celle du prefab : mêmes enfants, mêmes maillages, dans le même ordre.
            string Empreinte(Transform r) => string.Join("|", r.GetComponentsInChildren<Transform>(true).Select(x => (x == r ? "" : x.name) + ":" + (x.TryGetComponent<MeshFilter>(out var f) && f.sharedMesh ? f.sharedMesh.name : "")));
            if (Empreinte(piece) != Empreinte(du.Prefab.transform)) throw Faux("la pièce « " + nom + " » ne montre pas le prefab « " + prefab + " »");

            // La ligne du panneau, bâtie des chiffres du plan servi.
            string ligne = attendue == "fini" ? "Caserne : chantier achevé."
                : "Caserne : " + (attendue == "piquets" ? "aux piquets" : "aux murs") + ", " + TexteDuMonde.Jours(b.TravailFourni) + " de travail sur " + TexteDuMonde.Jours(b.TravailRequis) + ".";
            if (!Panneau().Split('\n').Contains(ligne)) throw Faux("panneau sans la ligne « " + ligne + " » : " + Panneau());
            if (attendue == "fini" && b.EnChantier) throw Faux("la caserne finie est encore en chantier au plan");

            var centre = piece.position;
            images.Add("{\"tick\":" + L(plan.Tick) + ",\"etape\":" + Q(attendue) + ",\"travail_fourni\":" + L(b.TravailFourni) + ",\"travail_requis\":" + L(b.TravailRequis)
                + ",\"batiment\":" + L(b.Identifiant) + ",\"parcelle\":" + L(b.Parcelle) + ",\"piece\":" + Q(piece.name) + ",\"prefab\":" + Q(prefab)
                + ",\"refus_du_devis_de_l_outil\":" + Q(outil.DevisDeLaLevee?.Batiment?.Refus) + ",\"panneau\":" + Q(Panneau())
                + ",\"x\":" + N(-centre.x) + ",\"y\":" + N(-centre.z) + ",\"lacet\":" + N(piece.eulerAngles.y) + ",\"ligne_du_panneau\":" + Q(ligne) + ",\"image\":null}");
            Ecrire("session interrompue après le relevé « " + attendue + " »");
            Debug.Log("CAPTURE_CASERNE relevé du tick " + L(plan.Tick) + " : " + attendue + ", " + b.TravailFourni + "/" + b.TravailRequis + ", " + prefab);
        }

        // La photo prise après ce scénario : sa durée dit combien il a pris de ses 60 s.
        static void Image(string nom)
        {
            string dernier = images[images.Count - 1];
            images[images.Count - 1] = dernier.Replace("\"image\":null", "\"image\":" + Q(nom) + ",\"duree_s\":" + N(Math.Round(Time.realtimeSinceStartupAsDouble - debutScenario, 1)));
            Ecrire("session interrompue après l'image « " + nom + " »");
            Debug.Log("CAPTURE_CASERNE image " + nom + " en " + (Time.realtimeSinceStartupAsDouble - debutScenario).ToString("F1", CultureInfo.InvariantCulture) + " s");
        }

        static Lecture<OrdresDeGuerre> Ordres(int port) => Task.Run(() => { using (var c = new ClientGuerre(port, TimeSpan.FromSeconds(60))) return c.LireOrdres(maison, null); }).GetAwaiter().GetResult();

        static string Ecrire(string defaut)
        {
            string r = "{\"cellule\":" + L(cellule) + ",\"port\":" + L(outil ? outil.Port : -1) + ",\"maison\":" + Q(maison) + ",\"tick_de_depart\":" + (tickDepart < 0 ? "null" : L(tickDepart))
                + ",\"part\":" + N(PartDuGrain) + ",\"route\":" + (rue < 0 ? "null" : L(rue)) + ",\"parcelle\":" + (parcelle < 0 ? "null" : L(parcelle)) + ",\"contour_de_la_parcelle\":" + contourParcelle
                + ",\"route_3d\":" + Q(routePosee) + ",\"camera\":" + (cadre == null ? "null" : "{\"distance\":" + N(cadre.Value.distance) + ",\"cap\":" + N(CapDeVue) + ",\"inclinaison\":" + N(InclinaisonDeVue) + "}")
                + ",\"clic\":" + P(CentreX, CentreY) + ",\"recu\":" + (recu == null ? "null" : "{\"acceptee\":" + (recu.Acceptee ? "true" : "false") + ",\"tick\":" + (recu.AppliqueeAuTick.HasValue ? L(recu.AppliqueeAuTick.Value) : "null") + "}")
                + ",\"devis\":[" + string.Join(",", devis) + "],\"images\":[" + string.Join(",", images) + "],\"defaut\":" + Q(defaut) + "}";
            File.WriteAllText(rapport, r + "\n", new UTF8Encoding(false)); return r;
        }

        static string Panneau() { var p = outil.view.transform.Find("Panneau des routes")?.GetComponent<TextMesh>(); if (!p) throw Faux("la caméra de l'outil n'a pas de panneau"); return p.text; }
        static bool Dans(Camera camera, Vector3 v) { var q = camera.WorldToViewportPoint(v); return q.z > camera.nearClipPlane && q.x > .02f && q.x < .98f && q.y > .02f && q.y < .98f; }
        static string Q(string s) => s == null ? "null" : "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r").Replace("\t", "\\t") + "\"";
        static string L(long n) => n.ToString(CultureInfo.InvariantCulture);
        static string N(double v) => v.ToString("R", CultureInfo.InvariantCulture);
        static string P(double x, double y) => "[" + N(x) + "," + N(y) + "]";
    }
}
