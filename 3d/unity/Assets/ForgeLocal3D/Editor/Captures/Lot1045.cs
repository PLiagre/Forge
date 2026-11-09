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
    // Lot 1045 : le feuillet « Le pays » écrit ce que `/pays` sert au tick du monde lu. Deux scénarios, joués dans l'ordre de leur nom, sur le même service :
    //   1. le petit seigneur : Bar-le-Duc choisi, le feuillet ouvert par un clic sur l'icône couronne, puis un moulin déposé par le chemin des intentions ;
    //   2. le royaume : le suzerain de Bar, posé côté Unity (le monde ne laisse pas encore prendre un royaume, #1037), le feuillet resté ouvert.
    // Le texte attendu s'écrit ici, d'après le format du brief, depuis trois lectures indépendantes (`/maisons`, `/lieu` par terre, `/pays`) :
    // ni `DossierPays.Decrire` ni `DossierPays.Registre` ne sont appelés. Contre-épreuve : `-forge1045Avance` pousse un tick avant le jugement :
    // le feuillet est resté au tick d'avant, le scénario échoue (« panneau lu au tick T, pays servi au tick T' »).
    static class Lot1045
    {
        const string AVANCE = "-forge1045Avance", TICKS_ARG = "-forgeTicks", SIEGE = "Bar-le-Duc", BANDEAU = "FORGE · Le cabinet";
        const string NON_NOMMEE = "maison non nommée", ABSENTE = "maison absente du registre";
        const int IMAGES = 10, LIMITE = 16000;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

        static CarteDessinee carte;
        static CabinetDeCarte cabinet;
        static DossierPays dossier;
        static Transform toile;
        static RectTransform cadre;
        static Button icone;
        static int port;
        static string bar, nomDeBar;
        static Lectures lectures;

        // Les deux lectures faites avant le jugement, hors de l'image : le nom de chaque maison, et celui de chaque lieu du pays.
        sealed class Lectures
        {
            public readonly Dictionary<string, string> Maisons = new Dictionary<string, string>();
            public readonly Dictionary<(long, long), string> Noms = new Dictionary<(long, long), string>();
        }
        // Ce que le jugement a vu, pour la trace et pour les jugements propres à chaque scénario.
        sealed class Releve
        {
            public TerresDuPays Pays; public string Texte, Nom, Suzerain; public string[] Lignes;
        }

        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause);
        static string N(long? v) => v == null ? "non servi" : v.Value.ToString(Inv);
        static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static bool Drapeau(string nom) => Environment.GetCommandLineArgs().Contains(nom);

        // Le parcours part du tick demandé au service : `-forgeTicks`, sinon le défaut de `ForgeCapture` (30), comme `Lot1032`.
        static long Depart()
        {
            var a = Environment.GetCommandLineArgs(); int i = Array.IndexOf(a, TICKS_ARG);
            return i >= 0 && i + 1 < a.Length ? long.Parse(a[i + 1], Inv) : 30;
        }

        [ScenarioDeCapture(1045, "pays-1-petit-seigneur")]
        static IEnumerator PetitSeigneur(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte();
            for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null; // étape 1
            carte = ouverte.Carte; port = carte.port;
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte");
            dossier = carte.GetComponent<DossierPays>() ?? throw Echec("étape 1 : pas de DossierPays sur la carte");
            toile = carte.transform.Find("Cabinet") ?? throw Echec("étape 1 : pas de toile du cabinet");
            cadre = (RectTransform)toile.Find(DossierPays.TITRE) ?? throw Echec("étape 1 : feuillet « " + DossierPays.TITRE + " » introuvable");
            icone = toile.Find(BANDEAU + "/" + CabinetDeCarte.PAYS + "/" + DossierPays.ICONE)?.GetComponent<Button>() ?? throw Echec("étape 1 : icône « " + DossierPays.ICONE + " » introuvable dans le bandeau");
            if (cadre.gameObject.activeSelf) throw Echec("étape 1 : le feuillet est ouvert d'avance");
            for (var e = Lot690.Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null; // étape 2
            // La toile sur la caméra de la photo, comme `Lot1032` : les jugements de cadre se font sur ce que l'image montre.
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f);
            var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases();

            var partie = cabinet.Partie; long depart = Depart(), tick = partie.Monde.Donnees.Monde.Tick;
            if (tick != depart) throw Echec("étape 3 : tick initial " + N(tick) + ", attendu " + N(depart) + " (" + TICKS_ARG + ")");
            var fiches = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (fiches.Length != 1) throw Echec("étape 3 : " + fiches.Length + " départs dont le siège est « " + SIEGE + " »");
            var choix = partie.Choisir(fiches[0].Id);
            for (var e = Lot690.Attendre(choix, "choix de " + SIEGE); e.MoveNext();) yield return null;
            if (partie.Recu == null || !partie.Recu.Acceptee) throw Echec("étape 3 : reçu du choix refusé : " + (partie.Recu == null ? "aucun reçu" : partie.Recu.Presente ? partie.Recu.Erreur : partie.Recu.Absence));
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            for (var e = Lot690.Jusqua(() => Lue(null, tick + 1), () => "étape 3 : " + Dire()); e.MoveNext();) yield return null;
            bar = cabinet.Partie.Monde.Donnees.MaisonDuJoueur;

            icone.onClick.Invoke();
            if (!cadre.gameObject.activeSelf) throw Echec("étape 4 : le clic sur l'icône « " + DossierPays.ICONE + " » n'ouvre pas le feuillet");
            for (var e = Prete(bar, tick + 1, "étape 4"); e.MoveNext();) yield return null;
            nomDeBar = Nom(bar);

            // Jugement R1 : le seigneur de Bar a son suzerain, et aucun bâtiment.
            Releve r1 = Juger(camera, bar, "étape 5, jugement R1");
            if (!r1.Lignes.Contains("Suzerain : Valois")) throw Echec("étape 5 : la ligne « Suzerain : Valois » manque : « " + Ligne(r1.Lignes[1]) + " »");
            if (Sous(r1, "BÂTIMENTS").Single() != "aucun") throw Echec("étape 5 : sous BÂTIMENTS, « " + string.Join(" | ", Sous(r1, "BÂTIMENTS")) + " » au lieu de « aucun »");

            // Le moulin de Bar par le chemin des intentions, celui du joueur.
            long siege = cabinet.Partie.Maison?.Donnees?.Siege.CellId ?? throw Echec("étape 6 : le siège de Bar n'a pas de terre lue");
            RecuIntention recu;
            using (var client = new ClientIntention(port, TimeSpan.FromSeconds(10)))
                recu = client.Deposer("{\"type\":\"batir_dans_une_province\",\"maison\":\"" + bar + "\",\"cell\":" + siege.ToString(Inv) + ",\"nature\":\"moulin\"}");
            if (!recu.Acceptee) throw Echec("étape 6 : le moulin est refusé : " + (recu.Presente ? recu.Erreur : recu.Absence));
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            for (var e = Prete(bar, r1.Pays.Tick + 1, "étape 7"); e.MoveNext();) yield return null;

            // Jugement R2 : le moulin est en chantier, une seule ligne sous BÂTIMENTS.
            Releve r2 = Juger(camera, bar, "étape 8, jugement R2");
            Moulin(r2, siege, "Moulin à " + SIEGE + " : en chantier, ", "étape 8");
            for (int i = 0; i < IMAGES; i++) yield return null;
            Releve r3 = Juger(camera, bar, "étape 9");
            Moulin(r3, siege, "Moulin à " + SIEGE + " : en chantier, ", "étape 9");
            Tracer("pays-1-petit-seigneur", r3, "");
        }

        [ScenarioDeCapture(1045, "pays-2-royaume")]
        static IEnumerator Royaume(Camera camera)
        {
            if (cabinet == null || bar == null || nomDeBar == null) throw Echec("étape 1 : le scénario pays-1-petit-seigneur n'a pas joué");
            // Le suzerain de Bar : une maison sans suzerain, qui tient plus de lieux que Bar.
            string suzerain;
            using (var client = new ClientMaison(port, TimeSpan.FromSeconds(10)))
            {
                var petit = client.LireComptes(bar); if (!petit.Presente || petit.Donnees.Suzerain == null) throw Echec("étape 1 : Bar n'a pas de suzerain : " + (petit.Absence ?? "suzerain nul"));
                suzerain = petit.Donnees.Suzerain; var haut = client.LireComptes(suzerain);
                if (!haut.Presente || haut.Donnees.Suzerain != null || haut.Donnees.Maison.Lieux.Count <= petit.Donnees.Maison.Lieux.Count)
                    throw Echec("étape 1 : le suzerain « " + suzerain + " » n'est pas un royaume : " + (haut.Absence ?? haut.Donnees.Maison.Lieux.Count + " lieux, suzerain " + (haut.Donnees.Suzerain ?? "nul")));
            }
            for (var e = Lot690.Jusqua(() => !cabinet.Partie.Occupee, () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            cabinet.Partie = Posee(suzerain);
            if (!cadre.gameObject.activeSelf) throw Echec("étape 2 : le feuillet n'est plus ouvert");
            for (var e = Prete(suzerain, null, "étape 2"); e.MoveNext();) yield return null;
            var defilement = cadre.GetComponentInChildren<ScrollRect>(true) ?? throw Echec("étape 2 : le feuillet n'a pas de lecture défilante");
            defilement.verticalNormalizedPosition = 1f; yield return null; Canvas.ForceUpdateCanvases();
            for (var e = Prete(suzerain, null, "étape 2, remis en haut"); e.MoveNext();) yield return null;

            // Jugement R1 : un royaume, sans suzerain, avec Bar parmi ses vassaux directs et le moulin de Bar.
            Releve r1 = Juger(camera, suzerain, "étape 3, jugement R1");
            Royal(r1, "étape 3");
            long tick = r1.Pays.Tick;
            for (var e = Pousser(1); e.MoveNext();) yield return null;
            for (var e = Prete(suzerain, tick + 1, "étape 4"); e.MoveNext();) yield return null;
            defilement.verticalNormalizedPosition = 1f; yield return null; Canvas.ForceUpdateCanvases();
            for (var e = Prete(suzerain, tick + 1, "étape 4, remis en haut"); e.MoveNext();) yield return null;
            Releve r2 = Juger(camera, suzerain, "étape 5, jugement R2");
            Royal(r2, "étape 5");
            if (r2.Lignes[0] == r1.Lignes[0]) throw Echec("étape 5 : l'en-tête n'a pas changé de jour : « " + r2.Lignes[0] + " »");
            for (int i = 0; i < IMAGES; i++) yield return null;
            Releve r3 = Juger(camera, suzerain, "étape 6"); Royal(r3, "étape 6");
            Tracer("pays-2-royaume", r3, " ; maison posée par le scénario");
        }

        // Remplace la lecture du cabinet par une lecture faite des sept clients de `LecturePartie.Locale`, dont le monde nomme la maison donnée : le service,
        // `/pays`, son tick et le feuillet sont les vrais ; seule la maison du joueur est posée ici.
        static LecturePartie Posee(string maison)
        {
            int p = port; var delai = TimeSpan.FromSeconds(10);
            return new LecturePartie(
                () => { using (var c = new ClientMonde(p, delai)) { var l = c.LireAvecMaison(); return l.Presente ? Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(l.Donnees.Monde, maison)) : l; } },
                id => { using (var c = new ClientMaison(p, delai)) return c.Lire(id); },
                () => { using (var c = new ClientDeparts(p, ClientDeparts.DelaiMinimal)) return c.Lire(); },
                id => RecuIntention.Absente("maison posée par le scénario"),
                id => { using (var c = new ClientMaison(p, delai)) return c.LireComptes(id); },
                id => { using (var c = new ClientPays(p, delai)) return c.Lire(id); },
                id => { using (var c = new ClientPays(p, delai)) return c.LireTerres(id); });
        }

        static IEnumerator Pousser(int n)
        {
            var poussee = Task.Run(() => { for (int i = 0; i < n; i++) { var r = Lot690.PousserTick(port).Result; if (r.statut != 200) return r; } return (200, ""); });
            for (var e = Lot690.Attendre(poussee, n + " tick(s)"); e.MoveNext();) yield return null;
            if (poussee.Result.Item1 != 200) throw Echec("tick " + poussee.Result.Item2);
        }

        // La partie est libre et a lu le monde et les terres du pays de `maison` (n'importe laquelle si nulle) au même tick (`tick`, n'importe lequel si nul).
        static bool Lue(string maison, long? tick)
        {
            var p = cabinet.Partie; var m = p.Monde; var y = p.Terres;
            if (p.Occupee || m == null || !m.Presente || m.Donnees.MaisonDuJoueur == null) return false;
            if (maison != null && m.Donnees.MaisonDuJoueur != maison || tick != null && m.Donnees.Monde.Tick != tick) return false;
            return y != null && y.Presente && y.Donnees.MaisonId == m.Donnees.MaisonDuJoueur && y.Donnees.Tick == m.Donnees.Monde.Tick;
        }

        static string Dire() => "partie " + Lot690.Dire(cabinet.Partie) + ", terres " + (cabinet.Partie.Terres == null ? "non lues" : !cabinet.Partie.Terres.Presente ? "absentes : " + cabinet.Partie.Terres.Absence : "au tick " + N(cabinet.Partie.Terres.Donnees.Tick));

        // Le feuillet écrit le pays de `id` : il commence par le nom de la maison et n'a plus de nom en cours de lecture.
        static bool Ecrit(string id)
        {
            string t = dossier.TexteAffiche;
            return t != null && lectures != null && t.StartsWith(Nom(id), StringComparison.Ordinal) && !t.Contains(NomsDesTerres.NomEnLecture);
        }

        // Attend la partie, lit les noms hors de l'image, attend le feuillet, laisse passer une image pour qu'il se redessine, et exige qu'il le soit encore.
        static IEnumerator Prete(string maison, long? tick, string quand)
        {
            for (var e = Lot690.Jusqua(() => Lue(maison, tick), () => quand + " : " + Dire()); e.MoveNext();) yield return null;
            string id = cabinet.Partie.Monde.Donnees.MaisonDuJoueur;
            var lecture = Task.Run(() => Lire(id));
            for (var e = Lot690.Attendre(lecture, quand + " : lectures du texte attendu"); e.MoveNext();) yield return null;
            lectures = lecture.Result;
            for (var e = Lot690.Jusqua(() => Lue(maison, tick) && Ecrit(id), () => quand + " : " + Dire() + ", feuillet « " + Ligne(dossier.TexteAffiche) + " »"); e.MoveNext();) yield return null;
            yield return null;
            for (var e = Lot690.Jusqua(() => Lue(maison, tick) && Ecrit(id), () => quand + " : " + Dire() + ", feuillet « " + Ligne(dossier.TexteAffiche) + " »"); e.MoveNext();) yield return null;
        }

        static string Nom(string id) => lectures.Maisons.TryGetValue(id, out string nom) ? nom ?? NON_NOMMEE : ABSENTE;

        // Les lectures indépendantes du feuillet : `/maisons`, puis `/lieu` pour chaque terre du pays. Chaque nom doit être servi.
        static Lectures Lire(string id)
        {
            var l = new Lectures();
            var registre = LectureDossier.Locale(port);
            registre.Actualiser("/maisons").GetAwaiter().GetResult();
            if (registre.Erreur != null || registre.Document == null) throw Echec("/maisons illisible : " + (registre.Erreur ?? "aucun document"));
            foreach (var brut in DocumentDuMonde.Tableau(registre.Document.Champs, "maisons"))
            {
                var m = (Dictionary<string, object>)brut;
                l.Maisons[DocumentDuMonde.Texte(m, "id")] = DocumentDuMonde.Valeur(m, "nom") as string;
            }
            Lecture<TerresDuPays> pays;
            using (var client = new ClientPays(port, TimeSpan.FromSeconds(10))) pays = client.LireTerres(id);
            if (!pays.Presente) throw Echec("pays de « " + id + " » absent : " + pays.Absence);
            var voulus = new SortedSet<(long, long)>();
            foreach (var lieu in pays.Donnees.Lieux.Concat(pays.Donnees.LieuxDesVassaux)) { voulus.Add((lieu.CellId, lieu.Rang)); voulus.Add((lieu.CellId, 0)); }
            foreach (var b in pays.Donnees.Batiments) voulus.Add((b.CellId, 0));
            foreach (long terre in voulus.Select(v => v.Item1).Distinct())
            {
                LectureLieu lue;
                using (var client = new ClientLieu(port, ClientDeparts.DelaiMinimal)) lue = client.Lire(terre);
                if (!lue.Presente) throw Echec("nom de lieu absent : " + terre.ToString(Inv) + " (" + lue.Absence + ")");
                foreach (var v in voulus.Where(v => v.Item1 == terre))
                {
                    string nom = lue.Lieu.Lieux?.FirstOrDefault(p => p.Rang == v.Item2)?.Nom;
                    if (nom == null) throw Echec("nom de lieu absent : " + terre.ToString(Inv));
                    l.Noms[v] = nom;
                }
            }
            return l;
        }

        // Le texte du feuillet, d'après le format du brief ; les noms sont ceux des lectures, jamais un identifiant.
        static string Attendu(TerresDuPays t)
        {
            string Maison(string id) => Nom(id);
            string Lieu(long c, long r) => lectures.Noms.TryGetValue((c, r), out string nom) ? nom : throw Echec("nom de lieu absent : " + c.ToString(Inv));
            string Compte(long n, string un, string plusieurs) => TexteDuMonde.Nombre(n) + " " + (n > 1 ? plusieurs : un);
            var l = new List<string>
            {
                Maison(t.MaisonId) + " · relevé au " + TexteDuMonde.Date(t.Date),
                "Suzerain : " + (t.Suzerain == null ? "aucun" : Maison(t.Suzerain)),
                "Vassaux : " + (t.Vassaux.Count == 0 ? "aucun" : Compte(t.Vassaux.Count, "maison", "maisons")),
                "", "GENS ET GRAIN",
                "Lieux : " + Compte(t.NombreDeLieux, "lieu", "lieux") + ", dont " + Compte(t.Lieux.Count, "lieu tenu", "lieux tenus") + " en propre",
                "Habitants : " + Compte(t.Habitants, "habitant", "habitants") + ", dont " + Compte(t.HabitantsPropres, "habitant", "habitants") + " sur ses propres lieux",
                "Récolte des trente derniers jours : " + TexteDuMonde.Masse(t.Recolte30jKg) + " de grain",
                "Grenier : " + (t.GrenierKg == null ? TexteDuMonde.Absence(t.AbsenceDuGrenier, t.MaisonId) : TexteDuMonde.Masse(t.GrenierKg.Value) + " de vivres"),
                "Greniers des vassaux : " + TexteDuMonde.Masse(t.GreniersDesVassauxKg) + " de vivres",
                "Chantiers des bourgs : " + Compte(t.Chantiers, "chantier", "chantiers") + " en cours",
                "", "BÂTIMENTS",
            };
            if (t.Batiments.Count == 0) l.Add("aucun");
            foreach (var b in t.Batiments)
                l.Add(b.Nom + " à " + Lieu(b.CellId, 0) + (b.Maison == t.MaisonId ? "" : ", de " + Maison(b.Maison)) + " : "
                    + (b.EnChantier ? "en chantier, " + TexteDuMonde.Jours(b.TravailFourni) + " de travail sur " + TexteDuMonde.Jours(b.TravailRequis) : "achevé"));
            l.Add(""); l.Add("SES LIEUX"); AjouterLesTerres(l, t.Lieux, Lieu);
            l.Add(""); l.Add("SES VASSAUX");
            l.Add(t.Vassaux.Count == 0 ? "aucun" : string.Join(", ", t.Vassaux.Select(Maison)));
            var autres = t.VassauxTous.Where(v => !t.Vassaux.Contains(v)).ToList();
            if (autres.Count > 0) l.Add("Par leurs vassaux (" + Compte(autres.Count, "maison", "maisons") + ") : " + string.Join(", ", autres.Select(Maison)));
            l.Add(""); l.Add("LIEUX DE SES VASSAUX"); AjouterLesTerres(l, t.LieuxDesVassaux, Lieu);
            return string.Join("\n", l);
        }

        // Une ligne par terre, dans l'ordre de leur première apparition ; dans une terre, les lieux suivent l'ordre des rangs.
        static void AjouterLesTerres(List<string> l, IReadOnlyList<LieuDuPays> lieux, Func<long, long, string> nom)
        {
            if (lieux.Count == 0) { l.Add("aucun"); return; }
            var terres = new List<long>();
            foreach (var lieu in lieux) if (!terres.Contains(lieu.CellId)) terres.Add(lieu.CellId);
            foreach (long terre in terres)
            {
                var rangs = lieux.Where(x => x.CellId == terre).Select(x => x.Rang).OrderBy(r => r).ToList();
                bool tenu = rangs.Contains(0); var autres = rangs.Where(r => r != 0).Select(r => nom(terre, r)).ToList();
                if (!tenu) l.Add("Autour de " + nom(terre, 0) + " : " + string.Join(", ", autres));
                else if (autres.Count == 0) l.Add(nom(terre, 0));
                else l.Add(nom(terre, 0) + " et " + TexteDuMonde.Nombre(autres.Count) + (autres.Count > 1 ? " lieux" : " lieu") + " : " + string.Join(", ", autres));
            }
        }

        // Les lignes d'un bloc : de la ligne qui suit son titre à la ligne vide.
        static string[] Sous(Releve r, string titre)
        {
            int i = Array.IndexOf(r.Lignes, titre); if (i < 0) throw Echec("titre « " + titre + " » absent du feuillet");
            return r.Lignes.Skip(i + 1).TakeWhile(x => x != "").ToArray();
        }

        static void Moulin(Releve r, long siege, string debut, string quand)
        {
            var lignes = Sous(r, "BÂTIMENTS");
            if (lignes.Length != 1 || !lignes[0].StartsWith(debut, StringComparison.Ordinal))
                throw Echec(quand + " : sous BÂTIMENTS, « " + string.Join(" | ", lignes) + " » ne se réduit pas à une ligne qui commence par « " + debut + " »");
            if (r.Pays.Batiments.Count != 1 || r.Pays.Batiments[0].Nature != "moulin" || r.Pays.Batiments[0].CellId != siege)
                throw Echec(quand + " : le pays servi compte " + r.Pays.Batiments.Count + " bâtiment(s), dont le premier est « " + (r.Pays.Batiments.Count > 0 ? r.Pays.Batiments[0].Nature : "aucun") + " » sur la terre " + (r.Pays.Batiments.Count > 0 ? N(r.Pays.Batiments[0].CellId) : "aucune") + " (siège " + N(siege) + ")");
        }

        static void Royal(Releve r, string quand)
        {
            if (!r.Lignes.Contains("Suzerain : aucun")) throw Echec(quand + " : la ligne « Suzerain : aucun » manque : « " + Ligne(r.Lignes[1]) + " »");
            if (r.Pays.Vassaux.Count <= 100) throw Echec(quand + " : " + r.Pays.Vassaux.Count + " vassaux directs, plus de 100 attendus");
            var directs = Sous(r, "SES VASSAUX").First().Split(new[] { ", " }, StringSplitOptions.None);
            if (!directs.Contains(nomDeBar)) throw Echec(quand + " : Bar (« " + nomDeBar + " ») n'est pas parmi les vassaux directs");
            string debut = "Moulin à " + SIEGE + ", de " + nomDeBar + " : en chantier, ";
            if (!Sous(r, "BÂTIMENTS").Any(x => x.StartsWith(debut, StringComparison.Ordinal)))
                throw Echec(quand + " : sous BÂTIMENTS, « " + string.Join(" | ", Sous(r, "BÂTIMENTS")) + " » sans ligne qui commence par « " + debut + " »");
        }

        // Relit `/pays` et juge le feuillet contre lui, dans la même image et sans `yield` : la première faute lève l'erreur.
        static Releve Juger(Camera camera, string id, string quand)
        {
            if (Drapeau(AVANCE)) { var un = Lot690.PousserTick(port).Result; if (un.statut != 200) throw Echec(quand + " : tick " + un.corps); }
            Lecture<TerresDuPays> servi; using (var client = new ClientPays(port, TimeSpan.FromSeconds(10))) servi = client.LireTerres(id);
            if (!servi.Presente) throw Echec(quand + " : pays de « " + id + " » absent : " + servi.Absence);
            TerresDuPays t = servi.Donnees; var partie = cabinet.Partie; var lue = partie.Terres;
            long? tickLu = lue != null && lue.Presente ? (long?)lue.Donnees.Tick : null;
            if (tickLu != t.Tick) throw Echec(quand + " : panneau lu au tick " + N(tickLu) + ", pays servi au tick " + N(t.Tick));
            long tickDuMonde = partie.Monde.Donnees.Monde.Tick;
            if (tickLu != tickDuMonde) throw Echec(quand + " : panneau lu au tick " + N(tickLu) + ", monde lu au tick " + N(tickDuMonde));

            string attendu = Attendu(t), ecrit = dossier.TexteAffiche ?? throw Echec(quand + " : le feuillet n'a rien écrit");
            string[] a = attendu.Split('\n'), e = ecrit.Split('\n');
            for (int i = 0; i < Math.Max(a.Length, e.Length); i++)
                if (i >= a.Length || i >= e.Length || a[i] != e[i])
                    throw Echec(quand + " : ligne " + (i + 1) + " : attendue « " + (i < a.Length ? a[i] : "(aucune)") + " », lue « " + (i < e.Length ? e[i] : "(aucune)") + " »");

            var ids = new List<string> { t.MaisonId };
            if (t.Suzerain != null) ids.Add(t.Suzerain);
            ids.AddRange(t.VassauxTous); ids.AddRange(t.Batiments.Select(b => b.Maison));
            if ((TexteDuMonde.Interdit(ecrit, ids.Distinct().ToArray()) ?? TexteDuMonde.SansUnite(ecrit)) is string refuse) throw Echec(quand + " : « " + refuse + " » refusé dans le feuillet");
            if (ecrit.Length > LIMITE) throw Echec(quand + " : " + ecrit.Length + " caractères, " + LIMITE + " au plus (ce qu'un Text d'Unity dessine en entier)");

            if (!cadre.gameObject.activeInHierarchy) throw Echec(quand + " : le feuillet « " + DossierPays.TITRE + " » n'est pas actif");
            var coins = new Vector3[4]; cadre.GetWorldCorners(coins);
            for (int i = 0; i < 4; i++)
            {
                Vector3 v = camera.WorldToViewportPoint(coins[i]);
                if (v.z <= 0f || v.x < -0.01f || v.x > 1.01f || v.y < -0.01f || v.y > 1.01f) throw Echec(quand + " : coin " + i + " du feuillet hors de l'image : " + v.ToString("F3"));
            }
            Text titre = cadre.GetComponentsInChildren<Text>(true).FirstOrDefault(x => x.name == DossierPays.TITRE) ?? throw Echec(quand + " : titre du feuillet introuvable");
            Lot690.DansLeChamp(camera, titre);
            var defilement = cadre.GetComponentInChildren<ScrollRect>(true) ?? throw Echec(quand + " : le feuillet n'a pas de lecture défilante");
            if (defilement.verticalNormalizedPosition < 0.999f) throw Echec(quand + " : la lecture du feuillet n'est pas en haut : " + defilement.verticalNormalizedPosition.ToString("F3", Inv));
            // L'icône se voit : dans l'image, et aucun autre bouton du bandeau ou de la toile ne la recouvre (le Menu lui cède la place).
            Rect pierre = Ecran(camera, (RectTransform)icone.transform), image = new Rect(0, 0, camera.pixelWidth, camera.pixelHeight);
            if (pierre.xMin < -0.5f || pierre.yMin < -0.5f || pierre.xMax > image.xMax + 0.5f || pierre.yMax > image.yMax + 0.5f) throw Echec(quand + " : icône hors de l'image : " + pierre + " dans " + image);
            foreach (var autre in toile.GetComponentsInChildren<Button>().Where(b => b != icone && b.transform.parent.name != DossierPays.TITRE && b.transform.parent.parent?.name != DossierPays.TITRE))
                if (Ecran(camera, (RectTransform)autre.transform).Overlaps(pierre)) throw Echec(quand + " : le bouton « " + autre.name + " » recouvre l'icône « " + DossierPays.ICONE + " » " + pierre);
            return new Releve { Pays = t, Texte = ecrit, Lignes = e, Nom = Nom(id), Suzerain = t.Suzerain == null ? null : Nom(t.Suzerain) };
        }

        static Rect Ecran(Camera camera, RectTransform r)
        {
            var coins = new Vector3[4]; r.GetWorldCorners(coins); var p = coins.Select(c => camera.WorldToScreenPoint(c)).ToArray();
            return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y));
        }

        static void Tracer(string scenario, Releve r, string ajout) =>
            Debug.Log("CAPTURE_1045 " + scenario + " pays « " + r.Nom + " » lu au tick " + N(cabinet.Partie.Terres.Donnees.Tick) + ", servi au tick " + N(r.Pays.Tick)
                + " : lieux " + r.Pays.NombreDeLieux.ToString(Inv) + ", vassaux directs " + r.Pays.Vassaux.Count.ToString(Inv) + ", bâtiments " + r.Pays.Batiments.Count.ToString(Inv)
                + ", suzerain « " + (r.Suzerain ?? "aucun") + " », caractères " + r.Texte.Length.ToString(Inv) + ajout);
    }
}
