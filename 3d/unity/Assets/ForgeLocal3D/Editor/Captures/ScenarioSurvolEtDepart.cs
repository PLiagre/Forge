using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace ForgeLocal3D.Captures
{
    // Le survol d'un lieu et le départ du joueur, sur le vrai service (un monde neuf, sans maison du joueur, l'accueil ouvert), photographiés six fois :
    //   1-survol-tournai                  l'infobulle du lieu sous Tournai : le pays d'abord (« Hainaut »), jamais la maison en tête ;
    //   2-survol-avignon                  celle d'Avignon : « États de l'Église » ;
    //   3-survol-pampelune-castillan      un lieu castillan de la terre de Pampelune, trouvé sous un point de l'écran par `LieuSous` : l'infobulle dit « Castille » ;
    //   4-accueil-guyenne                 la fiche de la Guyenne : « Guyenne : N habitants », puis sa maison avec ses vassaux, la carte cadrée sur le pays ;
    //   5-choix-navarre                   la Navarre choisie, « Commencer » pressé, le temps jamais lancé : l'horloge reste en pause à la même date, « Pause / Reprendre »
    //                                     porte l'engagement, le guide dit le choix reçu et l'encart écrit les gestes ;
    //   6-choix-navarre-plus-tard         au moins cinq secondes plus tard, la date et le tick servis n'ont pas bougé, et l'horloge est toujours en pause.
    // Chaque scénario vérifie ce qu'il photographie et échoue sinon. Aucune cellule n'est écrite en dur : villes, pays et lieux se trouvent par leur nom dans
    // ce que le service sert. Le tick est celui que le service sert. Le cabinet est une toile posée devant la caméra de la carte, que le cabinet garde
    // sur tout l'écran ; l'accueil ouvert couvre la droite de l'image, et chaque cadre se tient dans la part de carte qui reste à gauche.
    static class ScenarioSurvolEtDepart
    {
        const string GROUPE = "survol-et-depart", GUYENNE = "Guyenne", NAVARRE = "Navarre", CASTILLE = "Castille";
        const float DEMI_DU_SURVOL_KM = 60f, MARGE_DU_PAYS = 0.12f, BORD_DE_LA_PART = 0.04f;
        const int GRILLE_DES_LIEUX = 200, IMAGES_DE_POSE = 4;
        const double STABLE_S = 2.5; // les textes se récrivent une image après la lecture
        const double PLUS_TARD_S = 5;

        // Ce que « 5-choix-navarre » note, et que « 6-choix-navarre-plus-tard » relit.
        static DateDuMonde? dateNotee; static long tickNote = -1; static string texteNote;

        sealed class Texte { public string Valeur; }

        [ScenarioDeCapture(GROUPE, "1-survol-tournai")]
        static IEnumerator SurvolTournai(Camera camera)
        {
            var e = ScenarioAccueil.OuvrirLaCarte(); while (e.MoveNext()) yield return e.Current;
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var s = SurvolDuneVille(carte, cabinet, guerre, "Tournai", "Hainaut"); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "2-survol-avignon")]
        static IEnumerator SurvolAvignon(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            var s = SurvolDuneVille(carte, cabinet, guerre, "Avignon", "États de l'Église"); while (s.MoveNext()) yield return null;
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "3-survol-pampelune-castillan")]
        static IEnumerator SurvolPampelune(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Cacher(carte, cabinet);
            CelluleDeCarte cellule = null;
            var v = AttendreLaVille(carte, "Pampelune", ville => cellule = ville.cellule); while (v.MoveNext()) yield return null;
            long id = cellule.CellId;
            // Les lieux de la terre que les terres servies donnent à la Castille.
            var castillans = guerre.Terres.AutresPaysDe(id).Where(l => guerre.Terres.NomDuPays(guerre.Terres.PaysDuLieu(id, l.Rang)) == CASTILLE).Select(l => l.Rang).ToArray();
            if (castillans.Length == 0)
                throw Faux("la terre de Pampelune (" + id + ") n'a aucun lieu de « " + CASTILLE + " » : autres pays " + string.Join(", ", guerre.Terres.AutresPaysDe(id).Select(l => l.Rang + " " + guerre.Terres.NomDuPays(l.Pays))));
            var boite = Boite(carte, new[] { cellule });
            float part = PartDeLaCarte(carte, cabinet);
            Cadrer(carte, cabinet, guerre, boite, part);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            // Le lieu castillan est cherché sous les points de l'écran : le premier rang qu'un point rend par `LieuSous`.
            Vector2? ecran = null; long rang = -1; string essais = "";
            foreach (long r in castillans)
            {
                var trouve = ChercherUnPoint(carte, id, r, boite, part, out int candidats);
                essais += " rang " + r + " : " + candidats + " points de la terre, " + (trouve.HasValue ? "retenu" : "aucun à l'écran") + " ;";
                if (trouve.HasValue) { ecran = trouve; rang = r; break; }
            }
            if (!ecran.HasValue) throw Faux("aucun point de l'écran ne rend un lieu castillan de la terre " + id + " par LieuSous :" + essais);
            var texte = new Texte();
            var s = MontrerLInfobulle(carte, cabinet, guerre, ecran.Value, cellule, rang, "Pampelune, lieu castillan", CASTILLE, texte); while (s.MoveNext()) yield return null;
            Debug.Log("CAPTURE survol-et-depart : lieu " + rang + " de la terre " + id + " (Pampelune), à l'écran " + ecran.Value + " : « " + EnUneLigne(texte.Valeur) + " »");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "4-accueil-guyenne")]
        static IEnumerator AccueilGuyenne(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Cacher(carte, cabinet);
            string pays = guerre.Terres.Pays.SingleOrDefault(p => p.Nom == GUYENNE)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + GUYENNE + " »");
            var terres = guerre.Terres.Terres.Where(t => t.Pays == pays).ToArray();
            if (terres.Length == 0) throw Faux("échantillon vide : aucune terre servie n'est à « " + GUYENNE + " »");
            cabinet.Accueil.Designer(terres[0].CellId);
            var accueil = cabinet.Accueil;
            for (var a = AttentesDeCapture.Jusqua(() => accueil.TexteDuNom == GUYENNE && accueil.TexteDeLaFiche.StartsWith(GUYENNE + " : ", StringComparison.Ordinal) && !accueil.TexteDeLaFiche.Contains("en lecture"),
                () => "fiche de la Guyenne : « " + accueil.TexteDuNom + " » « " + accueil.TexteDeLaFiche + " »"); a.MoveNext();) yield return null;
            // La Guyenne cadrée dans la part de carte que l'accueil laisse à gauche.
            var cellules = carte.Lue.Cellules.Where(c => guerre.Terres.PaysDe(c.CellId) == pays).ToArray();
            if (cellules.Length == 0) throw Faux("échantillon vide : la carte ne dessine aucune terre de « " + GUYENNE + " »");
            Cadrer(carte, cabinet, guerre, Boite(carte, cellules), PartDeLaCarte(carte, cabinet), MARGE_DU_PAYS);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            string fiche = accueil.TexteDeLaFiche; string[] lignes = fiche.Split('\n');
            if (accueil.TexteDuNom != GUYENNE) throw Faux("le nom de l'accueil n'est pas « " + GUYENNE + " » : « " + accueil.TexteDuNom + " »");
            if (!fiche.StartsWith(GUYENNE + " : ", StringComparison.Ordinal)) throw Faux("la fiche ne commence pas par « " + GUYENNE + " : » : « " + fiche + " »");
            if (lignes.Length < 2 || !lignes[1].StartsWith("Maison", StringComparison.Ordinal)) throw Faux("la deuxième ligne de la fiche ne dit pas la maison : « " + fiche + " »");
            Debug.Log("CAPTURE survol-et-depart : accueil de la Guyenne au tick " + cabinet.Partie.Monde.Donnees.Monde.Tick + ", " + cellules.Length + " terres cadrées : « " + accueil.TexteDuNom + " » « " + EnUneLigne(fiche) + " »");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "5-choix-navarre")]
        static IEnumerator ChoixNavarre(Camera camera)
        {
            var (carte, cabinet, guerre) = ScenarioAccueil.Lire();
            Cacher(carte, cabinet);
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null, () => "l'horloge n'est pas servie : " + horloge.Absence); a.MoveNext();) yield return null;
            // Le monde s'ouvre en pause : la promesse. Il n'est pas mis en pause ici ; s'il court, la promesse est rompue.
            if (!horloge.EnPause) throw Faux("le monde ne s'ouvre pas en pause : " + horloge.Lue.JoursParSeconde.ToString("R", CultureInfo.InvariantCulture) + " jours par seconde avant le choix");
            string pays = guerre.Terres.Pays.SingleOrDefault(p => p.Nom == NAVARRE)?.Id ?? throw Faux("aucun pays servi ne s'appelle « " + NAVARRE + " »");
            var terres = guerre.Terres.Terres.Where(t => t.Pays == pays).ToArray();
            if (terres.Length == 0) throw Faux("échantillon vide : aucune terre servie n'est à « " + NAVARRE + " »");
            var accueil = cabinet.Accueil;
            accueil.Designer(terres[0].CellId);
            for (var a = AttentesDeCapture.Jusqua(() => accueil.TexteDuNom == NAVARRE && accueil.Montree != null && accueil.Commencer.interactable,
                () => "fiche de la Navarre : « " + accueil.TexteDuNom + " » « " + accueil.TexteDeLaFiche + " », « Commencer » " + (accueil.Commencer.interactable ? "actif" : "inactif")); a.MoveNext();) yield return null;
            var cellules = carte.Lue.Cellules.Where(c => guerre.Terres.PaysDe(c.CellId) == pays).ToArray();
            if (cellules.Length > 0) Cadrer(carte, cabinet, guerre, Boite(carte, cellules), PartDeLaCarte(carte, cabinet), MARGE_DU_PAYS);
            string dateAvant = HorlogeDeCarte.Decrire(horloge.Lue); long tickAvant = horloge.Lue.Tick;
            // « Commencer » seul : jamais « Reprendre », jamais `CommencerPuisLancer`, qui lance le temps.
            accueil.Commencer.onClick.Invoke();
            for (var a = AttentesDeCapture.Jusqua(() => cabinet.Partie.Recu?.Acceptee == true,
                () => "le choix n'est pas reçu : « " + (cabinet.Partie.Recu?.Erreur ?? cabinet.Partie.Recu?.Absence) + " »"); a.MoveNext();) yield return null;
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            // L'horloge est relue toutes les 0,25 s : une lecture au moins est passée depuis le clic.
            var lue = horloge.Lue;
            if (!horloge.EnPause) throw Faux("le temps ne reste pas en pause après le choix : " + horloge.Lue.JoursParSeconde.ToString("R", CultureInfo.InvariantCulture) + " jours par seconde");
            if (!cabinet.TempsMisEnAvant) throw Faux("« Pause / Reprendre » ne porte pas l'engagement après le choix reçu");
            Text guide = cabinet.transform.Find("Cabinet").GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.name == CabinetDeCarte.GUIDE) ?? throw Faux("le guide « " + CabinetDeCarte.GUIDE + " » est absent du cabinet");
            if (!guide.gameObject.activeInHierarchy || guide.text != CabinetDeCarte.CHOIX_RECU) throw Faux("le guide ne dit pas « " + CabinetDeCarte.CHOIX_RECU + " » : « " + guide.text + " », " + (guide.gameObject.activeInHierarchy ? "visible" : "caché"));
            if (!cabinet.Gestes.Visible || cabinet.Gestes.TexteDesGestes != PremiersGestes.GESTES) throw Faux("l'encart des gestes n'écrit pas « " + PremiersGestes.GESTES + " » : « " + cabinet.Gestes.TexteDesGestes + " », " + (cabinet.Gestes.Visible ? "visible" : "caché"));
            string dateApres = HorlogeDeCarte.Decrire(lue);
            if (dateApres != dateAvant || lue.Tick != tickAvant) throw Faux("la date a bougé entre le clic et la lecture : « " + EnUneLigne(dateAvant) + " » tick " + tickAvant + " devient « " + EnUneLigne(dateApres) + " » tick " + lue.Tick);
            dateNotee = lue.Date; tickNote = lue.Tick; texteNote = dateApres;
            Debug.Log("CAPTURE survol-et-depart : la Navarre choisie, le temps en pause au tick " + tickNote + ", date servie jour " + lue.Date.JourDeLAnnee + " de " + lue.Date.Annee + ", bandeau « " + EnUneLigne(texteNote)
                + " » ; guide « " + guide.text + " » ; encart « " + cabinet.Gestes.TexteDesGestes + " »");
            yield return carte.camera;
        }

        [ScenarioDeCapture(GROUPE, "6-choix-navarre-plus-tard")]
        static IEnumerator ChoixNavarrePlusTard(Camera camera)
        {
            var (carte, cabinet, _) = ScenarioAccueil.Lire();
            if (dateNotee == null) throw Faux("aucune date notée : « 5-choix-navarre » n'a pas réussi");
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Faux("pas d'horloge sur la carte");
            var avant = horloge.Lue; double depuis = Time.realtimeSinceStartupAsDouble;
            while (Time.realtimeSinceStartupAsDouble - depuis < PLUS_TARD_S) yield return null;
            // L'horloge a pu être relue : elle lit le service toutes les 0,25 s ; la preuve est qu'elle l'ait été.
            for (var a = AttentesDeCapture.Jusqua(() => horloge.Lue != null && !ReferenceEquals(horloge.Lue, avant), () => "l'horloge n'est pas relue : " + horloge.Absence); a.MoveNext();) yield return null;
            var s = ScenarioAccueil.Stabiliser(cabinet); while (s.MoveNext()) yield return null;
            var lue = horloge.Lue; var date = lue.Date;
            if (!horloge.EnPause) throw Faux("l'horloge n'est plus en pause : " + lue.JoursParSeconde.ToString("R", CultureInfo.InvariantCulture) + " jours par seconde");
            if (date.Annee != dateNotee.Value.Annee || date.JourDeLAnnee != dateNotee.Value.JourDeLAnnee || lue.Tick != tickNote)
                throw Faux("le temps a avancé sans « Reprendre » : jour " + dateNotee.Value.JourDeLAnnee + " de " + dateNotee.Value.Annee + " tick " + tickNote + " devient jour " + date.JourDeLAnnee + " de " + date.Annee + " tick " + lue.Tick);
            if (HorlogeDeCarte.Decrire(lue) != texteNote) throw Faux("le bandeau a changé : « " + EnUneLigne(texteNote) + " » devient « " + EnUneLigne(HorlogeDeCarte.Decrire(lue)) + " »");
            if (!cabinet.TempsMisEnAvant) throw Faux("« Pause / Reprendre » ne porte plus l'engagement");
            Debug.Log("CAPTURE survol-et-depart : plus tard (" + (Time.realtimeSinceStartupAsDouble - depuis).ToString("0.#", CultureInfo.InvariantCulture) + " s), toujours en pause au tick " + lue.Tick + ", jour " + date.JourDeLAnnee + " de " + date.Annee + ", bandeau « " + EnUneLigne(texteNote) + " »");
            yield return carte.camera;
        }

        // Le survol d'une ville nommée : la vue la cadre dans la part de carte libre, son point d'écran donne le lieu par `SolSous` puis `LieuSous`,
        // et l'infobulle de ce lieu, en mode automatique, dit d'abord son pays.
        static IEnumerator SurvolDuneVille(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, string nom, string pays)
        {
            Cacher(carte, cabinet);
            Vector3 ici = default; CelluleDeCarte cellule = null;
            var v = AttendreLaVille(carte, nom, ville => { ici = ville.ici; cellule = ville.cellule; }); while (v.MoveNext()) yield return null;
            float part = PartDeLaCarte(carte, cabinet);
            Poser(carte, cabinet, guerre, new Vector2(ici.x, ici.z), DEMI_DU_SURVOL_KM, part);
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null;
            Vector2 ecran = EcranDe(carte, new Vector2(ici.x, ici.z), part, nom);
            var sol = carte.SolSous(ecran) ?? throw Faux("aucun sol sous le point d'écran " + ecran + " de « " + nom + " »");
            var lieu = carte.LieuSous(sol) ?? throw Faux("aucun lieu sous le point d'écran " + ecran + " de « " + nom + " »");
            if (lieu.cellule.CellId != cellule.CellId) throw Faux("le point d'écran de « " + nom + " » tombe sur la terre " + lieu.cellule.CellId + ", pas sur la sienne (" + cellule.CellId + ")");
            var texte = new Texte();
            var s = MontrerLInfobulle(carte, cabinet, guerre, ecran, lieu.cellule, lieu.rang, nom, pays, texte); while (s.MoveNext()) yield return null;
            Debug.Log("CAPTURE survol-et-depart : " + nom + " (terre " + lieu.cellule.CellId + ", lieu " + lieu.rang + ", écran " + ecran + ") : « " + EnUneLigne(texte.Valeur) + " »");
        }

        // L'infobulle du lieu au point d'écran, lue puis fixée pendant STABLE_S ; elle commence par le pays attendu, sur sa propre ligne, jamais par une maison.
        static IEnumerator MontrerLInfobulle(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector2 ecran, CelluleDeCarte cellule, long rang, string quoi, string pays, Texte rendu)
        {
            var bulle = carte.GetComponent<InfobulleDeTerre>() ?? throw Faux("pas d'infobulle de terre sur la carte");
            bulle.automatique = true;
            void Pas() => bulle.Pas(ecran, cellule, Time.realtimeSinceStartupAsDouble, rang);
            bool Lu() { string t = bulle.TexteAffiche; return t != null && !t.Contains("en lecture") && !t.Contains(DossierTerritoire.ATTENTE) && !t.Contains("Lecture indisponible"); }
            Pas();
            for (var a = AttentesDeCapture.Jusqua(() => { Pas(); return Lu(); }, () => "infobulle de « " + quoi + " » non lue : « " + bulle.TexteAffiche + " »"); a.MoveNext();) yield return null;
            string avant = bulle.TexteAffiche; double depuis = Time.realtimeSinceStartupAsDouble, fin = depuis + 20;
            while (Time.realtimeSinceStartupAsDouble - depuis < STABLE_S && Time.realtimeSinceStartupAsDouble < fin)
            {
                yield return null; Pas();
                if (bulle.TexteAffiche != avant) { avant = bulle.TexteAffiche; depuis = Time.realtimeSinceStartupAsDouble; }
            }
            string texte = bulle.TexteAffiche;
            if (!Lu() || Time.realtimeSinceStartupAsDouble - depuis < STABLE_S) throw Faux("l'infobulle de « " + quoi + " » ne se fixe pas : « " + texte + " »");
            if (!texte.StartsWith(pays + "\n", StringComparison.Ordinal)) throw Faux("l'infobulle de « " + quoi + " » ne commence pas par « " + pays + " » seul sur sa ligne : « " + EnUneLigne(texte) + " »");
            if (texte.StartsWith("Maison : ", StringComparison.Ordinal)) throw Faux("l'infobulle de « " + quoi + " » commence par la maison : « " + EnUneLigne(texte) + " »");
            rendu.Valeur = texte;
        }

        // Cache l'infobulle d'un scénario précédent : le feuillet et le texte noté.
        static void Cacher(CarteDessinee carte, CabinetDeCarte cabinet)
        {
            var bulle = carte.GetComponent<InfobulleDeTerre>();
            if (bulle != null) bulle.Pas(Vector2.zero, null, Time.realtimeSinceStartupAsDouble);
            Infobulle.Cacher(cabinet.transform.Find("Cabinet").GetComponent<Canvas>());
        }

        // La ville de ce nom et sa terre, par la carte servie ; sinon par l'atlas (les capitales que la carte ne nomme pas), dont le pied se lit
        // dans la terre sous lui. Le point rendu est en km locaux, sur le sol. Nul : ni l'une ni l'autre ne la sert (encore).
        static (Vector3 ici, CelluleDeCarte cellule)? ChercherLaVille(CarteDessinee carte, string nom)
        {
            if (carte.Lue == null) return null;
            foreach (var cellule in carte.Lue.Cellules)
                foreach (var ville in cellule.Villes)
                    if (ville.Nom == nom && carte.PositionSurLaCarte(ville.Position, 0f) is Vector3 place) return (place, cellule);
            var villes = carte.GetComponent<VillesDeCarte>();
            if (villes != null)
                foreach (var capitale in villes.Capitales)
                    if (capitale.nom == nom && carte.CelluleSous(carte.transform.TransformPoint(capitale.pied)) is CelluleDeCarte terre) return (capitale.pied, terre);
            return null;
        }

        // La ville de ce nom, attendue le temps que l'atlas se lise ; absente de la carte comme de l'atlas, le scénario échoue.
        static IEnumerator AttendreLaVille(CarteDessinee carte, string nom, Action<(Vector3 ici, CelluleDeCarte cellule)> rendre)
        {
            for (var a = AttentesDeCapture.Jusqua(() => ChercherLaVille(carte, nom) != null, () => "ni la carte ni l'atlas ne servent la ville « " + nom + " »"); a.MoveNext();) yield return null;
            rendre(ChercherLaVille(carte, nom).Value);
        }

        // La part de la largeur de l'image que l'accueil ouvert laisse à la carte : le bord gauche de son panneau, lu sur la caméra de la carte.
        static float PartDeLaCarte(CarteDessinee carte, CabinetDeCarte cabinet)
        {
            Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4]; cabinet.Accueil.Panneau.GetWorldCorners(coins);
            float bord = coins.Min(c => carte.camera.WorldToViewportPoint(c).x);
            if (!(bord > 0f && bord < 1f)) throw Faux("le panneau de l'accueil ne laisse pas de carte à gauche (bord à " + bord.ToString("0.###", CultureInfo.InvariantCulture) + " de l'image)");
            return bord;
        }

        // La vue sur ce point (km locaux), tenu au milieu de la part de carte libre ; la toile, la caméra et les noms suivent.
        static void Poser(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, Vector2 point, float demi, float part)
        {
            float aspect = carte.camera.aspect;
            carte.Vue.Changer(aspect); carte.Vue.Centrer(point + new Vector2(demi * aspect * (1f - part), 0f), demi); carte.Vue.Poser(carte.camera, carte.transform);
            cabinet.transform.Find("Cabinet").GetComponent<Canvas>().planeDistance = carte.camera.nearClipPlane + ScenarioAccueil.ECART_DE_PLAN;
            guerre.SuivreLaVue();
        }

        // La boîte tenue dans la part de carte libre, élargie de `marge` de chaque côté (en part de sa taille) ; jamais plus près que la vue la plus proche.
        static void Cadrer(CarteDessinee carte, CabinetDeCarte cabinet, CarteDeLaGuerre guerre, (Vector2 min, Vector2 max) boite, float part, float marge = 0.1f)
        {
            Vector2 taille = boite.max - boite.min, centre = (boite.min + boite.max) / 2f; float aspect = carte.camera.aspect;
            float demi = Mathf.Max(VueDeCarte.DEMI_MIN_KM, taille.y * (1f + 2f * marge) / 2f, taille.x * (1f + 2f * marge) / 2f / (aspect * part));
            Poser(carte, cabinet, guerre, centre, demi, part);
        }

        // La boîte des contours extérieurs de ces cellules, en km locaux de la carte (mètres servis moins l'origine, en km).
        static (Vector2 min, Vector2 max) Boite(CarteDessinee carte, IEnumerable<CelluleDeCarte> cellules)
        {
            PointCarte origine = carte.Origine ?? throw Faux("la carte posée n'a pas d'origine");
            Vector2 min = new Vector2(float.PositiveInfinity, float.PositiveInfinity), max = new Vector2(float.NegativeInfinity, float.NegativeInfinity);
            foreach (var cellule in cellules)
                foreach (var polygone in cellule.Contour)
                    foreach (PointCarte p in polygone.Exterieur)
                    {
                        var km = new Vector2((float)((p.X - origine.X) / 1000.0), (float)((p.Y - origine.Y) / 1000.0));
                        min = Vector2.Min(min, km); max = Vector2.Max(max, km);
                    }
            if (float.IsInfinity(min.x)) throw Faux("aucun contour servi à cadrer");
            return (min, max);
        }

        static Vector3 Monde(CarteDessinee carte, Vector2 km) => carte.transform.TransformPoint(new Vector3(km.x, 0f, km.y));

        // Le point d'écran d'un point du sol (km locaux), posé sur le relief ; il doit tenir dans la part de carte libre, sans toucher ses bords.
        static Vector2 EcranDe(CarteDessinee carte, Vector2 km, float part, string quoi)
        {
            Vector3 v = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(carte.SurLeSol(km.x, km.y, 0f)));
            if (v.z <= 0f || v.x < BORD_DE_LA_PART || v.x > part - BORD_DE_LA_PART || v.y < BORD_DE_LA_PART || v.y > 1f - BORD_DE_LA_PART)
                throw Faux("« " + quoi + " » n'est pas dans la part de carte libre : à l'image " + v + ", part " + part.ToString("0.###", CultureInfo.InvariantCulture));
            return carte.camera.WorldToScreenPoint(carte.transform.TransformPoint(carte.SurLeSol(km.x, km.y, 0f)));
        }

        // Un point d'écran dont `LieuSous` rend ce lieu de cette terre : la boîte de la terre est balayée en grille, puis les points trouvés
        // sont essayés du plus central au plus excentré, chacun relu par l'écran (`SolSous`, `LieuSous`) comme le fait la souris.
        static Vector2? ChercherUnPoint(CarteDessinee carte, long cellId, long rang, (Vector2 min, Vector2 max) boite, float part, out int candidats)
        {
            var trouves = new List<Vector2>(); Vector2 taille = boite.max - boite.min;
            for (int j = 0; j < GRILLE_DES_LIEUX; j++)
                for (int i = 0; i < GRILLE_DES_LIEUX; i++)
                {
                    var km = boite.min + new Vector2((i + .5f) / GRILLE_DES_LIEUX * taille.x, (j + .5f) / GRILLE_DES_LIEUX * taille.y);
                    var lieu = carte.LieuSous(Monde(carte, km));
                    if (lieu.HasValue && lieu.Value.cellule.CellId == cellId && lieu.Value.rang == rang) trouves.Add(km);
                }
            candidats = trouves.Count;
            if (trouves.Count == 0) return null;
            Vector2 centre = trouves.Aggregate(Vector2.zero, (s, k) => s + k) / trouves.Count;
            foreach (var km in trouves.OrderBy(k => (k - centre).sqrMagnitude))
            {
                Vector3 v = carte.camera.WorldToViewportPoint(carte.transform.TransformPoint(carte.SurLeSol(km.x, km.y, 0f)));
                if (v.z <= 0f || v.x < BORD_DE_LA_PART || v.x > part - BORD_DE_LA_PART || v.y < BORD_DE_LA_PART || v.y > 1f - BORD_DE_LA_PART) continue;
                Vector2 ecran = carte.camera.WorldToScreenPoint(carte.transform.TransformPoint(carte.SurLeSol(km.x, km.y, 0f)));
                var sol = carte.SolSous(ecran); var relu = sol.HasValue ? carte.LieuSous(sol.Value) : null;
                if (relu.HasValue && relu.Value.cellule.CellId == cellId && relu.Value.rang == rang) return ecran;
            }
            return null;
        }

        static string EnUneLigne(string texte) => texte == null ? "(aucun texte)" : texte.Replace("\n", " | ");

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("survol et départ : " + raison);
    }
}
