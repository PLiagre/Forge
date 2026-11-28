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
    // Ce que l'écran dit d'un pays, d'un lieu et d'un mode de carte, sans se contredire, sur le vrai service (avec l'IA : -forgeServiceIa),
    // en 1920 × 1080, une image à chaque pas :
    //   01-bar                       le Duché de Bar choisi (la seigneurie 1), le monde en pause, la vue sur Bar-le-Duc ;
    //   02-survol-bar-france         le lieu français de la province de Bar-le-Duc : l'infobulle dit la France et la province partagée, la terre est gardée ;
    //   03-survol-desert             un lieu des Tribus du désert : « Terre sans État », jamais une maison ;
    //   04-survol-constantinople     le bourg de Constantinople ;
    //   05-politique à 09-guerres    les cinq modes de carte, chacun d'un clic sur son bouton, la légende fixe.
    // Le survol passe par `InfobulleDeTerre` au point d'écran du lieu (trouvé par le relief, comme la souris), la terre gardée par le chemin du
    // clic du cabinet. Chaque pas échoue si un nom des listes de noms-1400.json ou d'une dynastie est écrit à la place d'un pays ; si l'infobulle,
    // la fiche de la terre gardée et les noms de pays écrits sur le lieu ne disent pas le même pays ; si une légende dit « rouge » ; si la
    // capitale du joueur porte deux étiquettes à l'écran ; et chaque pas exige l'état que le précédent a laissé. Le tick est celui que le service
    // sert, jamais écrit en dur.
    static class ScenarioSurvolEtLegendes
    {
        const string GROUPE = "survol-et-legendes", PAUSE = "Pause / Reprendre", NOM_DU_DESERT = "Tribus du désert", FRANCE = "puissance-3", MAISON_DE_BAR = "seigneurie-1";
        const int LARGEUR = 1920, HAUTEUR = 1080, IMAGES_DE_POSE = 4, SEIGNEURIE = 1;
        const long BAR_LE_DUC = 10430, CONSTANTINOPLE = 10374;
        const float DEMI_DE_BAR_KM = 90f, DEMI_DU_SURVOL_KM = 60f, DEMI_DES_MODES_KM = 450f, RAYON_DE_RECHERCHE_PX = 240f, PAS_DE_RECHERCHE_PX = 6f;
        const double STABLE_S = 2.5; // les textes sont récrits une image après la lecture

        enum Etape { Aucune, Bar, SurvolBarFrance, SurvolDesert, SurvolConstantinople, Politique, Relief, Population, Vivres, Guerres }

        // Ce qu'un pas laisse au suivant : la maison du joueur, son pays, son siège (km locaux), le tick servi.
        sealed class Partie { public string Maison, Pays; public Vector3 Siege; public long Tick; public Etape Faite; }
        static Partie enCours;

        [ScenarioDeCapture(GROUPE, "01-bar", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P1(Camera c) => Pas(Etape.Bar);
        [ScenarioDeCapture(GROUPE, "02-survol-bar-france", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P2(Camera c) => Pas(Etape.SurvolBarFrance);
        [ScenarioDeCapture(GROUPE, "03-survol-desert", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P3(Camera c) => Pas(Etape.SurvolDesert);
        [ScenarioDeCapture(GROUPE, "04-survol-constantinople", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P4(Camera c) => Pas(Etape.SurvolConstantinople);
        [ScenarioDeCapture(GROUPE, "05-politique", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P5(Camera c) => Pas(Etape.Politique);
        [ScenarioDeCapture(GROUPE, "06-relief", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P6(Camera c) => Pas(Etape.Relief);
        [ScenarioDeCapture(GROUPE, "07-population", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P7(Camera c) => Pas(Etape.Population);
        [ScenarioDeCapture(GROUPE, "08-vivres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P8(Camera c) => Pas(Etape.Vivres);
        [ScenarioDeCapture(GROUPE, "09-guerres", Largeur = LARGEUR, Hauteur = HAUTEUR)] static IEnumerator P9(Camera c) => Pas(Etape.Guerres);

        // Un pas : le geste de l'étape, puis ce que tout pas vérifie ; la photo est celle de la caméra de la carte.
        static IEnumerator Pas(Etape etape)
        {
            if (etape != Etape.Bar && (enCours == null || enCours.Faite != etape - 1))
                throw Faux(etape + " : le pas d'avant n'a pas réussi (dernier fait : " + (enCours == null ? "aucun" : enCours.Faite.ToString()) + ")");
            IEnumerator geste;
            switch (etape)
            {
                case Etape.Bar: geste = Bar(); break;
                case Etape.SurvolBarFrance: geste = SurvolDeBar(); break;
                case Etape.SurvolDesert: geste = SurvolDuDesert(); break;
                case Etape.SurvolConstantinople: geste = SurvolDeConstantinople(); break;
                case Etape.Politique: geste = Mode(ModeDeCarte.Politique, true); break;
                case Etape.Relief: geste = Mode(ModeDeCarte.Relief, false); break;
                case Etape.Population: geste = Mode(ModeDeCarte.Population, false); break;
                case Etape.Vivres: geste = Mode(ModeDeCarte.Vivres, false); break;
                default: geste = Mode(ModeDeCarte.Guerres, false); break;
            }
            while (geste.MoveNext()) yield return geste.Current;
            VerifierLEcran(etape.ToString());
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Poser(carte, cabinet, guerre);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            enCours.Faite = etape;
            var horloge = Horloge(carte);
            Debug.Log("CAPTURE survol et légendes : " + etape + " au tick " + horloge.Lue?.Tick + (horloge.EnPause ? " (en pause)" : "") + ", centre " + carte.Vue.Centre + ", demi " + carte.Vue.Demi.ToString("0.#", CultureInfo.InvariantCulture) + " km");
            yield return carte.camera;
        }

        // Le service relancé, la carte rouverte, le Duché de Bar choisi, le monde en pause au jour poussé, la vue sur Bar-le-Duc.
        static IEnumerator Bar()
        {
            var o = Rouvrir(); while (o.MoveNext()) yield return o.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var horloge = Horloge(carte);
            var p = enCours = new Partie { Tick = Capture.JoursPousses };
            GestesDeCapture.Deposer(carte.port, "{\"type\":\"choisir_depart\",\"seigneurie\":" + SEIGNEURIE + "}");
            for (var e = ScenarioGuerre.Pousser(1, t => p.Tick = t); e.MoveNext();) yield return null;
            for (var a = AttentesDeCapture.Jusqua(() => ScenarioAccueil.Servie(cabinet) != null && cabinet.Partie.Maison?.Presente == true && !cabinet.Accueil.Ouvert && horloge.Lue != null,
                () => "aucune maison du joueur servie après le choix de la seigneurie " + SEIGNEURIE + " (horloge " + (horloge.Lue == null ? horloge.Absence : "servie") + ")"); a.MoveNext();) yield return null;
            p.Maison = ScenarioAccueil.Servie(cabinet);
            if (p.Maison != MAISON_DE_BAR) throw Faux("la seigneurie " + SEIGNEURIE + " sert la maison « " + p.Maison + " », attendu « " + MAISON_DE_BAR + " »");
            // Le monde court-il ? Alors la pause se joue comme le joueur : un clic sur son bouton.
            if (!horloge.EnPause)
            {
                GestesDeCapture.CliquerAuPointeur(carte.camera, Bouton(cabinet, PAUSE));
                for (var a = AttentesDeCapture.Jusqua(() => horloge.EnPause, () => "le clic sur « " + PAUSE + " » ne met pas le monde en pause : " + horloge.Lue?.JoursParSeconde + " jours par seconde"); a.MoveNext();) yield return null;
            }
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue.Tick == p.Tick && Relire(guerre, p.Tick), () => "horloge au tick " + horloge.Lue?.Tick + ", terres du tick " + guerre.Terres?.Tick + ", attendu " + p.Tick); a.MoveNext();) yield return null;
            p.Pays = guerre.PaysDeLaMaison(p.Maison);
            var siege = cabinet.Partie.Maison.Donnees.Siege;
            if (siege.CellId != BAR_LE_DUC) throw Faux("le siège de « " + p.Maison + " » est la terre " + siege.CellId + ", attendu " + BAR_LE_DUC + " (Bar-le-Duc)");
            p.Siege = Siege(carte, cabinet);
            Viser(carte, cabinet, guerre, p.Siege, DEMI_DE_BAR_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var nom = guerre.NomsDesPays.FirstOrDefault(n => n.Pays == p.Pays) ?? throw Faux("le pays du joueur (« " + guerre.Terres.NomDuPays(p.Pays) + " ») n'a pas de nom écrit sur la carte");
            if (nom.Masque || nom.Opacite <= 0f) throw Faux("le nom « " + nom.Texte + " » du pays du joueur n'est pas écrit à " + DEMI_DE_BAR_KM + " km : masque " + nom.Masque + ", opacité " + nom.Opacite);
            Debug.Log("CAPTURE survol et légendes : « " + nom.Texte + " » écrit à " + nom.CorpsPx.ToString("0", CultureInfo.InvariantCulture) + " px, maison " + p.Maison + ", pays " + p.Pays + ", tick " + p.Tick);
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
        }

        // Le premier lieu de Bar-le-Duc qui est de la France : l'infobulle dit la France et la province partagée.
        static IEnumerator SurvolDeBar()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var lu = new LieuxDeLaTerre(); var l = LireLeLieu(carte, BAR_LE_DUC, lu); while (l.MoveNext()) yield return l.Current;
            long? rang = lu.Rangs.Where(r => guerre.Terres.PaysDuLieu(BAR_LE_DUC, r) == FRANCE).Select(r => (long?)r).FirstOrDefault();
            if (rang == null) throw Faux("aucun lieu de la terre " + BAR_LE_DUC + " n'est de « " + FRANCE + " » : pays des lieux " + string.Join(", ", lu.Rangs.Select(r => r + " " + guerre.Terres.PaysDuLieu(BAR_LE_DUC, r))));
            var s = Survol(BAR_LE_DUC, rang.Value, lu, exigerPartage: true, sansEtat: false); while (s.MoveNext()) yield return s.Current;
        }

        // Un lieu de la terre sans État des Tribus du désert, de préférence sous une lettre de leur nom : « Terre sans État », jamais une maison.
        static IEnumerator SurvolDuDesert()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var (cell, rang) = LieuDuDesert(carte, guerre);
            var lu = new LieuxDeLaTerre(); var l = LireLeLieu(carte, cell, lu); while (l.MoveNext()) yield return l.Current;
            var s = Survol(cell, rang, lu, exigerPartage: false, sansEtat: true); while (s.MoveNext()) yield return s.Current;
        }

        static IEnumerator SurvolDeConstantinople()
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var lu = new LieuxDeLaTerre(); var l = LireLeLieu(carte, CONSTANTINOPLE, lu); while (l.MoveNext()) yield return l.Current;
            var s = Survol(CONSTANTINOPLE, 0, lu, exigerPartage: false, sansEtat: false); while (s.MoveNext()) yield return s.Current;
        }

        // Ce que `/lieu` sert d'une terre : les rangs de ses lieux, et la place de chacun quand elle est servie.
        sealed class LieuxDeLaTerre { public List<long> Rangs = new List<long>(); public Dictionary<long, PointCarte> Places = new Dictionary<long, PointCarte>(); }

        static IEnumerator LireLeLieu(CarteDessinee carte, long cell, LieuxDeLaTerre rendu)
        {
            int port = carte.port;
            var tache = Task.Run(() => { using (var c = new ClientLieu(port, ScenarioGuerre.DELAI)) return c.Lire(cell); });
            for (var e = AttentesDeCapture.Attendre(tache, "lecture du lieu de la terre " + cell); e.MoveNext();) yield return null;
            if (!tache.Result.Presente) throw Faux("la terre " + cell + " n'est pas servie : " + tache.Result.Absence);
            var lieux = tache.Result.Lieu.Lieux ?? throw Faux("la terre " + cell + " ne sert pas ses lieux : " + tache.Result.Lieu.AbsenceDesLieux);
            foreach (var lieu in lieux.OrderBy(x => x.Rang)) { rendu.Rangs.Add(lieu.Rang); if (lieu.Position is PointCarte p) rendu.Places[lieu.Rang] = p; }
            if (rendu.Rangs.Count == 0) throw Faux("échantillon vide : la terre " + cell + " n'a aucun lieu servi");
        }

        // Le lieu (cell, rang) survolé par l'infobulle, puis gardé comme un clic du joueur ; ce que les trois écrans disent du pays s'accorde.
        static IEnumerator Survol(long cell, long rang, LieuxDeLaTerre lu, bool exigerPartage, bool sansEtat)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            string quoi = "le lieu " + rang + " de la terre " + cell;
            var cellule = carte.Lue.Cellules.FirstOrDefault(c => c.CellId == cell) ?? throw Faux("la terre " + cell + " n'est pas dessinée");
            string pays = guerre.Terres.PaysDuLieu(cell, rang), nomDuPays = guerre.Terres.NomDuPays(pays);
            bool sansMaison = pays == null || guerre.Terres.MaisonDuPays(pays) == null;
            if (sansEtat && !sansMaison) throw Faux(quoi + " est du pays « " + nomDuPays + " », qui a une maison : ce n'est pas une terre sans État");
            if (!sansEtat && sansMaison && exigerPartage) throw Faux(quoi + " n'est d'aucun pays tenu");
            Cacher(carte, cabinet);
            Vector3 ici = lu.Places.TryGetValue(rang, out PointCarte place) && carte.PositionSurLaCarte(place, 0f) is Vector3 v ? v : Centre(carte, cell);
            Viser(carte, cabinet, guerre, ici, DEMI_DU_SURVOL_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector2 point = PointDuLieu(carte, cabinet, cell, rang, ici);
            // L'infobulle, en mode automatique, lue puis fixée.
            var bulle = carte.GetComponent<InfobulleDeTerre>() ?? throw Faux("pas d'infobulle de terre sur la carte");
            bulle.automatique = true;
            void Survoler() => bulle.Pas(point, cellule, Time.realtimeSinceStartupAsDouble, rang);
            bool Lue(string t) => t != null && !t.Contains("en lecture") && !t.Contains(DossierTerritoire.ATTENTE) && !t.Contains("Lecture indisponible") && !t.Contains("Dossier incomplet");
            Survoler();
            for (var a = AttentesDeCapture.Jusqua(() => { Survoler(); return Lue(bulle.TexteAffiche); }, () => "infobulle de " + quoi + " non lue : « " + EnUneLigne(bulle.TexteAffiche) + " »"); a.MoveNext();) yield return null;
            var f = Fixer(() => { Survoler(); return bulle.TexteAffiche; }, "l'infobulle de " + quoi); while (f.MoveNext()) yield return null;
            string infobulle = bulle.TexteAffiche;
            // La terre gardée comme le joueur la garde : le point survolé, appui puis relâché au même point.
            var fiche = carte.GetComponent<FicheDeCellule>() ?? throw Faux("pas de fiche de cellule sur la carte");
            fiche.Survoler(point);
            if (fiche.Survolee == null || fiche.Survolee.CellId != cell) throw Faux("le point " + point + " tombe sur la terre " + fiche.Survolee?.CellId + ", pas sur " + cell);
            cabinet.Noter(point, true, false, false, fiche.Survolee, rang);
            if (!cabinet.Noter(point, false, true, false, fiche.Survolee, rang)) throw Faux("le clic en " + point + " sur " + quoi + " ne garde pas la terre");
            var dossier = carte.GetComponent<DossierTerritoire>() ?? throw Faux("pas de dossier du territoire sur la carte");
            for (var a = AttentesDeCapture.Jusqua(() => Lue(dossier.TexteAffiche) && dossier.TexteAffiche.Split('\n')[0] == infobulle.Split('\n')[0],
                () => "la fiche de " + quoi + " ne dit pas la première ligne de l'infobulle « " + EnUneLigne(infobulle.Split('\n')[0]) + " » : « " + EnUneLigne(dossier.TexteAffiche) + " »"); a.MoveNext();) yield return null;
            f = Fixer(() => { Survoler(); return dossier.TexteAffiche + "|" + bulle.TexteAffiche; }, "la fiche de " + quoi); while (f.MoveNext()) yield return null;
            string fichee = dossier.TexteAffiche; infobulle = bulle.TexteAffiche;
            // Le même pays dit par l'infobulle, par la fiche, par le pays servi du lieu et par chaque nom de pays écrit sur ce lieu.
            string ligne = infobulle.Split('\n')[0], ligneDeLaFiche = fichee.Split('\n')[0];
            if (ligne != ligneDeLaFiche) throw Faux("l'infobulle dit « " + ligne + " » et la fiche « " + ligneDeLaFiche + " » pour " + quoi);
            string[] mots = ligne.Split(new[] { " · " }, StringSplitOptions.None);
            string premier = sansMaison ? DossierTerritoire.SANS_ETAT : nomDuPays;
            if (mots[0] != premier) throw Faux("la première ligne de " + quoi + " commence par « " + mots[0] + " », attendu « " + premier + " » : « " + ligne + " »");
            if (sansMaison && pays != null && (mots.Length < 2 || mots[1] != nomDuPays)) throw Faux("la terre sans État de " + quoi + " ne dit pas son pays « " + nomDuPays + " » : « " + ligne + " »");
            if (sansEtat && (!ligne.StartsWith(DossierTerritoire.SANS_ETAT + " · ", StringComparison.Ordinal) || ligne.Contains("Maison"))) throw Faux("la première ligne du lieu sans État dit « " + ligne + " »");
            if (nomDuPays != null) TextesDeCapture.Verifier(new[] { nomDuPays }, "le pays de " + quoi);
            if (exigerPartage)
            {
                string province = infobulle.Split('\n').FirstOrDefault(t => t.StartsWith("Province ", StringComparison.Ordinal)) ?? throw Faux("l'infobulle de " + quoi + " n'a pas de ligne de province : « " + EnUneLigne(infobulle) + " »");
                if (!province.Contains("partagée") || !province.Contains("France")) throw Faux("la ligne de province « " + province + " » ne dit pas « partagée » et « France »");
            }
            var ecrits = NomsSur(carte, guerre, cell, rang, seulementMontres: true).ToList();
            foreach (var nom in ecrits)
                if (nom.Pays != pays || nom.Texte != nomDuPays) throw Faux("le nom « " + nom.Texte + " » (pays « " + nom.Pays + " ») est écrit sur " + quoi + ", qui est du pays « " + pays + " » (« " + nomDuPays + " »)");
            if (ecrits.Count == 0)
                Debug.Log("CAPTURE survol et légendes : aucune lettre d'un nom de pays montré ne tombe sur " + quoi + " ; noms non montrés qui y tombent : "
                    + string.Join(", ", NomsSur(carte, guerre, cell, rang, seulementMontres: false).Select(n => n.Texte + " (" + (n.Masque ? "masqué" : "opacité " + n.Opacite.ToString("0.##", CultureInfo.InvariantCulture)) + ")")));
            Debug.Log("CAPTURE survol et légendes : " + quoi + " au point " + point + ", pays « " + nomDuPays + " » ; infobulle « " + EnUneLigne(infobulle) + " » ; fiche « " + EnUneLigne(fichee) + " » ; noms écrits dessus : " + (ecrits.Count == 0 ? "aucun" : string.Join(", ", ecrits.Select(n => n.Texte))));
        }

        // Les noms de pays dont une lettre tombe sur ce lieu ; sans `seulementMontres`, les noms masqués ou transparents comptent aussi.
        static IEnumerable<NomCourbe> NomsSur(CarteDessinee carte, CarteDeLaGuerre guerre, long cell, long rang, bool seulementMontres)
        {
            var terrain = carte.Terrain ?? throw Faux("la carte n'a pas de terrain");
            foreach (var nom in guerre.NomsDesPays)
            {
                if (nom.Compose == null || seulementMontres && (nom.Masque || nom.Opacite <= 0f)) continue;
                for (int i = 0; i < Math.Min(nom.Ecrit.Length, nom.Compose.Lettres.Count); i++)
                {
                    if (char.IsWhiteSpace(nom.Ecrit[i])) continue;
                    Vector2 p = nom.Compose.Lettres[i].Point; ushort n = terrain.LieuEn(p.x, p.y);
                    if (n == 0) continue;
                    if (carte.Lue.Cellules[terrain.CelluleDuLieu(n - 1)].CellId == cell && terrain.RangDuLieu(n - 1) == rang) { yield return nom; break; }
                }
            }
        }

        // Un lieu des Tribus du désert (retrouvées par leur nom servi) : le premier, par terre, que couvre une lettre de leur nom ; à défaut le bourg de la première terre dessinée.
        static (long cell, long rang) LieuDuDesert(CarteDessinee carte, CarteDeLaGuerre guerre)
        {
            var terrain = carte.Terrain ?? throw Faux("la carte n'a pas de terrain");
            string desert = guerre.Terres.Pays.SingleOrDefault(p => p.Nom == NOM_DU_DESERT)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + NOM_DU_DESERT + " »");
            var dessinees = new HashSet<long>(carte.Lue.Cellules.Select(c => c.CellId));
            var terres = guerre.Terres.Terres.Where(t => t.Pays == desert && dessinees.Contains(t.CellId)).OrderBy(t => t.CellId).ToList();
            if (terres.Count == 0) throw Faux("échantillon vide : aucune terre dessinée n'est du pays « " + NOM_DU_DESERT + " »");
            var sous = new SortedSet<(long, long)>();
            foreach (var nom in guerre.NomsDesPays.Where(n => n.Pays == desert && n.Compose != null))
                for (int i = 0; i < Math.Min(nom.Ecrit.Length, nom.Compose.Lettres.Count); i++)
                {
                    if (char.IsWhiteSpace(nom.Ecrit[i])) continue;
                    Vector2 p = nom.Compose.Lettres[i].Point; ushort n = terrain.LieuEn(p.x, p.y);
                    if (n == 0) continue;
                    long cell = carte.Lue.Cellules[terrain.CelluleDuLieu(n - 1)].CellId, rang = terrain.RangDuLieu(n - 1);
                    if (guerre.Terres.PaysDuLieu(cell, rang) == desert) sous.Add((cell, rang));
                }
            return sous.Count > 0 ? sous.First() : (terres[0].CellId, 0L);
        }

        // Un point d'écran, libre de l'interface, dont le relief rend ce lieu : le plus près de la place du lieu, cherché en spirale.
        static Vector2 PointDuLieu(CarteDessinee carte, CabinetDeCarte cabinet, long cell, long rang, Vector3 ici)
        {
            Vector2 centre = Ecran(carte, carte.SurLeSol(ici.x, ici.z, 0f));
            bool Bon(Vector2 p)
            {
                if (!Dedans(p) || cabinet.HorsCarte(p)) return false;
                var sol = carte.SolSous(p); var lieu = sol.HasValue ? carte.LieuSous(sol.Value) : null;
                return lieu.HasValue && lieu.Value.cellule.CellId == cell && lieu.Value.rang == rang;
            }
            int n = Mathf.RoundToInt(RAYON_DE_RECHERCHE_PX / PAS_DE_RECHERCHE_PX);
            var ecarts = Enumerable.Range(-n, 2 * n + 1).SelectMany(i => Enumerable.Range(-n, 2 * n + 1).Select(j => new Vector2(i, j) * PAS_DE_RECHERCHE_PX))
                .Where(v => v.magnitude <= RAYON_DE_RECHERCHE_PX).OrderBy(v => v.sqrMagnitude).ThenBy(v => v.x).ThenBy(v => v.y);
            foreach (Vector2 ecart in ecarts) if (Bon(centre + ecart)) return centre + ecart;
            throw Faux("aucun point de l'écran, libre de l'interface, ne rend le lieu " + rang + " de la terre " + cell + " autour de " + centre);
        }

        // Un mode choisi d'un clic sur son bouton : lui seul enfoncé, la vue immobile, la légende disponible, datée et fixe.
        // Au premier, la vue se pose sur Bar-le-Duc, assez loin pour lire les pays.
        static IEnumerator Mode(ModeDeCarte mode, bool reculer)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire(); var horloge = Horloge(carte);
            var calques = carte.GetComponent<CalquesCarte>() ?? throw Faux("pas de calques sur la carte");
            Cacher(carte, cabinet);
            if (reculer) Viser(carte, cabinet, guerre, enCours.Siege, DEMI_DES_MODES_KM);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector2 centre = carte.Vue.Centre; float demi = carte.Vue.Demi;
            GestesDeCapture.CliquerAuPointeur(carte.camera, calques.BoutonDu(mode));
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            if (calques.Mode != mode) throw Faux("le clic sur « " + mode + " » ne change pas le mode : " + calques.Mode);
            string enfonces = string.Join(", ", ((ModeDeCarte[])Enum.GetValues(typeof(ModeDeCarte))).Where(calques.Enfonce));
            if (enfonces != mode.ToString()) throw Faux("boutons enfoncés : « " + enfonces + " » pour le mode " + mode);
            if (carte.Vue.Centre != centre || carte.Vue.Demi != demi) throw Faux("choisir « " + mode + " » a bougé la vue");
            string Texte() => calques.Legende.GetComponentInParent<Infobulle>().Phrase;
            bool Indisponible() => Texte().StartsWith("Mode ", StringComparison.Ordinal) || Texte().StartsWith("Pays indisponibles", StringComparison.Ordinal) || Texte().StartsWith(CalquesCarte.COUPEE, StringComparison.Ordinal);
            string jour = TexteDuMonde.Date(horloge.Lue.Date);
            bool Datee() => mode == ModeDeCarte.Relief || Texte().Contains(jour) || mode == ModeDeCarte.Guerres && calques.Legende.text == BelligerantsDesPays.AUCUNE_ARMEE;
            for (var a = AttentesDeCapture.Jusqua(() => !Indisponible() && Datee(), () => "légende du mode " + mode + " : « " + Texte() + " », l'horloge dit « " + jour + " »"); a.MoveNext();) yield return null;
            if (!horloge.EnPause || TexteDuMonde.Date(horloge.Lue.Date) != jour) throw Faux("la date a bougé pendant le mode " + mode + " : « " + jour + " » puis « " + TexteDuMonde.Date(horloge.Lue.Date) + " »");
            var f = Fixer(() => calques.Legende.text + "|" + string.Join("|", calques.EtiquettesDeLEchelle.Select(t => t.text)) + "|" + Texte(), "la légende du mode " + mode); while (f.MoveNext()) yield return null;
            Debug.Log("CAPTURE survol et légendes : mode " + mode + " ; légende « " + EnUneLigne(calques.Legende.text) + " » ; échelle « " + string.Join(" | ", calques.EtiquettesDeLEchelle.Select(t => t.text)) + " » ; infobulle « " + EnUneLigne(Texte()) + " »");
        }

        // Ce que tout pas vérifie : aucun nom inventé ni de dynastie, aucune légende qui dise « rouge », aucune capitale du joueur étiquetée deux fois.
        static void VerifierLEcran(string quoi)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            TextesDeCapture.Verifier(guerre, cabinet, quoi); ScenarioAccueil.VerifierLesNoms(guerre);
            var calques = carte.GetComponent<CalquesCarte>() ?? throw Faux("pas de calques sur la carte");
            var dits = calques.EtiquettesDeLEchelle.Select(t => "étiquette « " + t.text + " »").Concat(new[] { "légende « " + calques.Legende.text + " »", "infobulle de la légende « " + calques.Legende.GetComponentInParent<Infobulle>().Phrase + " »" })
                .Where(t => t.IndexOf("rouge", StringComparison.OrdinalIgnoreCase) >= 0).ToList();
            if (dits.Count > 0) throw Faux(quoi + " : la légende parle de rouge : " + string.Join(" ; ", dits.Select(EnUneLigne)));
            var villes = carte.GetComponent<VillesDeCarte>() ?? throw Faux("pas de villes sur la carte");
            var capitales = villes.Capitales.Where(c => c.pays.Contains(enCours.Pays)).ToList();
            if (capitales.Count == 0) throw Faux(quoi + " : le pays du joueur (« " + guerre.Terres.NomDuPays(enCours.Pays) + " ») n'a pas de capitale posée sur la carte");
            var toile = cabinet.transform.Find("Cabinet");
            var montrees = carte.GetComponentsInChildren<Text>(false).Where(t => t.isActiveAndEnabled && !t.transform.IsChildOf(toile)).ToList();
            foreach (var c in capitales)
            {
                int n = montrees.Count(t => t.text == c.nom || c.texte != null && t.text == c.texte.text);
                if (n > 1) throw Faux(quoi + " : la capitale « " + c.nom + " » du joueur porte " + n + " étiquettes à l'écran");
            }
        }

        // Tant que `lire` change, attend ; échoue s'il ne se fixe pas pendant STABLE_S.
        static IEnumerator Fixer(Func<string> lire, string quoi)
        {
            string avant = lire(); double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null; string maintenant = lire();
                if (maintenant != avant) { avant = maintenant; depuis = Time.realtimeSinceStartupAsDouble; }
            }
            if (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S) throw Faux(quoi + " ne se fixe pas : « " + EnUneLigne(lire()) + " »");
        }

        // Le service relancé et la carte rouverte, sa caméra rendant dans un écran de la taille de la photo.
        static IEnumerator Rouvrir()
        {
            Capture.RelancerLeService();
            var o = ScenarioAccueil.OuvrirLaCarte(); while (o.MoveNext()) yield return o.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            if (carte.camera.targetTexture == null) carte.camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24) { name = "Écran de survol et légendes" };
            carte.camera.aspect = (float)LARGEUR / HAUTEUR; carte.Vue.Changer(carte.camera.aspect); Poser(carte, cabinet, guerre);
        }

        // La carte de la guerre relue au tick servi : la lecture suivante est demandée tout de suite, sans attendre sa période.
        static bool Relire(CarteDeLaGuerre guerre, long tick)
        {
            if (guerre.Terres != null && guerre.Terres.Tick >= tick) return true;
            guerre.Pas(Time.realtimeSinceStartupAsDouble + CarteDeLaGuerre.PERIODE_S);
            return false;
        }

        // Cache l'infobulle d'un pas précédent : son feuillet et son texte.
        static void Cacher(CarteDessinee carte, CabinetDeCarte cabinet)
        {
            var bulle = carte.GetComponent<InfobulleDeTerre>();
            if (bulle != null) bulle.Pas(Vector2.zero, null, Time.realtimeSinceStartupAsDouble);
            Infobulle.Cacher(cabinet.transform.Find("Cabinet").GetComponent<Canvas>());
        }

        // La vue posée sur `ici` (km locaux) à `demi` km de demi-hauteur.
        static void Viser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector3 ici, float demi)
        {
            carte.Vue.Changer(carte.camera.aspect); carte.Vue.Centrer(new Vector2(ici.x, ici.z), demi); Poser(carte, cabinet, guerre);
        }

        static void Poser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre)
        {
            carte.Vue.Poser(carte.camera, carte.transform);
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;
            guerre.SuivreLaVue();
        }

        static HorlogeDeCarte Horloge(CarteDessinee carte) => carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
        static Button Bouton(CabinetDeCarte cabinet, string nom) =>
            cabinet.transform.Find("Cabinet").GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == nom) ?? throw Faux("« " + nom + " » absent du cabinet");
        static bool Dedans(Vector2 ecran) => ecran.x >= 0f && ecran.x < LARGEUR && ecran.y >= 0f && ecran.y < HAUTEUR;
        static Vector2 Ecran(CarteDessinee carte, Vector3 local) => carte.camera.WorldToScreenPoint(carte.transform.TransformPoint(local));
        // Le siège servi de la maison du joueur, en km locaux de la carte, au niveau de la mer.
        static Vector3 Siege(CarteDessinee carte, CabinetDeCarte cabinet) =>
            cabinet.Partie.Maison?.Donnees.Siege.Position is PointCarte p && carte.PositionSurLaCarte(p, 0f) is Vector3 v ? v : throw Faux("le siège de la maison du joueur n'est pas placé sur la carte");
        // Le milieu du plus grand contour d'une terre servie, en km locaux de la carte.
        static Vector3 Centre(CarteDessinee carte, long cellId)
        {
            var cellule = carte.Lue.Cellules.FirstOrDefault(c => c.CellId == cellId) ?? throw Faux("la terre " + cellId + " n'est pas dessinée");
            var points = cellule.Contour.OrderByDescending(c => c.Exterieur.Count).First().Exterieur.Select(x => carte.PositionSurLaCarte(x, 0f)).Where(v => v.HasValue).Select(v => v.Value).ToList();
            if (points.Count == 0) throw Faux("la terre " + cellId + " n'a pas de contour sur la carte");
            return points.Aggregate(Vector3.zero, (s, v) => s + v) / points.Count;
        }

        static string EnUneLigne(string texte) => texte == null ? "(aucun texte)" : texte.Replace("\n", " | ");

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("survol et légendes : " + raison);
    }
}
