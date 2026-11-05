using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 965 : la preuve du geste « Les modes de carte ». La photo du lot 658 (Mistra, 60 %, trente jours, le feuillet ouvert) passe par Puissances, Habitants et Flux : une seule légende, entière, sur aucun panneau, aucun nombre servi changé, chaque icône dit sa phrase.
    // Contre-épreuves : `-forge965DeuxLegendes` pose une copie de la légende en Flux, `-forge965Remonter` remonte la légende sur le feuillet, `-forge965Tick` pousse un tick avant les clics, `-forge965Muet` éteint le repère du Flux.
    static class Lot965 {
        const string DEUX = "-forge965DeuxLegendes", REMONTER = "-forge965Remonter", TICK = "-forge965Tick", MUET = "-forge965Muet", FEUILLET = "Terres et comptes", BULLE = "Infobulle";
        static readonly string[] FLOTTANTES = { "Légende des lieux", "Légende des flèches", "Fond de la légende", "Fond des flèches" }, DOSSIERS = { "FORGE · Le cabinet", "Votre maison", "Territoire conservé", "Parcourir le monde" }, EXCLUS = { "Fond des dossiers", CalquesCarte.LEGENDE, CalquesCarte.BANDE };
        const double STABLE_S = 2.5; // plus que la relecture du cabinet (1 s), des lieux et des flèches (2 s)
        static readonly Vector2 ANCIENNE = new Vector2(16, -104); // la place de l'ancienne légende des lieux, sur le feuillet
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string Ligne(string t) => (t ?? "(aucun)").Replace("\r", "").Replace("\n", " | ");
        static Rect Ecran(Camera camera, RectTransform cadre) { var coins = new Vector3[4]; cadre.GetWorldCorners(coins); var p = coins.Select(c => camera.WorldToScreenPoint(c)).ToArray(); return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y)); }
        static Camera camera; static Transform toile; static CabinetDeCarte cabinet; static HorlogeDeCarte horloge; static CalquesCarte calques; static long tickHorloge, tickMonde; static double vitesse; static string[] textes; // les nombres servis notés à l'étape 2
        static bool Drapeau(string d) => Environment.GetCommandLineArgs().Contains(d); static string N(long v) => v.ToString(CultureInfo.InvariantCulture);
        static bool Dans(Rect r) => r.xMin >= -.5f && r.yMin >= -.5f && r.xMax <= camera.pixelWidth + .5f && r.yMax <= camera.pixelHeight + .5f;
        static int Lignes(string texte) => Math.Max(CalquesCarte.Lignes(calques.Legende, texte, 1f), CalquesCarte.Lignes(calques.Legende, texte, 2f / 3f));
        static RectTransform Feuillet() => toile.Cast<Transform>().OfType<RectTransform>().SingleOrDefault(t => t.name == FEUILLET && t.GetComponentInChildren<ScrollRect>(true) != null) ?? throw Echec("feuillet « " + FEUILLET + " » introuvable");
        static bool Pret() => !cabinet.Partie.Occupee && !horloge.RequeteEnVol && horloge.Lue != null && cabinet.Partie.Monde?.Presente == true;
        static string[] Textes() => DOSSIERS.Select(n => toile.Find(n) ?? throw Echec("« " + n + " » introuvable")).Append(Feuillet()).OrderBy(p => p.GetSiblingIndex()).SelectMany(p => p.GetComponentsInChildren<Text>(false)).Where(t => t.isActiveAndEnabled).Select(t => t.text).ToArray();
        [ScenarioDeCapture(965, "trois-modes")] static IEnumerator TroisModes(Camera vue) {
            for (var e = Lot658.FlechesDuSiege(vue); e.MoveNext();) yield return null; camera = vue; CarteDessinee carte = Lot658.carte; toile = Lot658.toile; // étape 1
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte"); horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : pas d'horloge"); calques = carte.GetComponent<CalquesCarte>() ?? throw Echec("étape 1 : pas de CalquesCarte"); LieuxDeCarte lieux = carte.GetComponent<LieuxDeCarte>() ?? throw Echec("étape 1 : pas de LieuxDeCarte");
            (carte.GetComponent<SurvolDeCarte>() ?? throw Echec("étape 1 : pas de survol")).automatique = true; (carte.GetComponent<ParcoursDeCarte>() ?? throw Echec("étape 1 : pas de parcours")).automatique = true; (carte.GetComponent<InfobulleDeTerre>() ?? throw Echec("étape 1 : pas d'InfobulleDeTerre")).automatique = true; Canvas canvas = toile.GetComponent<Canvas>(); Infobulle.Cacher(canvas);
            // Étape 2. Le cabinet récrit ses dossiers dans son Update, et une lecture de la partie peut finir après lui dans la même image : les textes ne sont notés que restés identiques STABLE_S secondes.
            string[] vus = null; double depuis = 0; bool Stable() { var lus = Textes(); double ici = Time.realtimeSinceStartupAsDouble; if (vus == null || !lus.SequenceEqual(vus)) { vus = lus; depuis = ici; return false; } return ici - depuis >= STABLE_S && Pret() && horloge.Lue.Tick == cabinet.Partie.Monde.Donnees.Monde.Tick; } // l'horloge a presque toujours une lecture en vol : elle n'est exigée prête qu'à l'instant de noter
            for (var e = Lot690.Jusqua(Stable, () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie) + ", horloge " + (horloge.Lue == null ? "non lue" : "au tick " + N(horloge.Lue.Tick)) + ", textes " + (vus == null ? "non notés" : "changés il y a " + (Time.realtimeSinceStartupAsDouble - depuis).ToString("0.0", CultureInfo.InvariantCulture) + " s")); e.MoveNext();) yield return null;
            tickHorloge = horloge.Lue.Tick; vitesse = horloge.Lue.JoursParSeconde; tickMonde = cabinet.Partie.Monde.Donnees.Monde.Tick; textes = vus;
            if (Drapeau(TICK)) { var un = Lot690.PousserTick(carte.port); for (var e = Lot690.Attendre(un, "tick"); e.MoveNext();) yield return null; if (un.Result.statut != 200) throw Echec("tick " + un.Result.corps);
                for (var e = Lot690.Jusqua(() => Pret() && horloge.Lue.Tick == tickHorloge + 1 && cabinet.Partie.Monde.Donnees.Monde.Tick == tickMonde + 1, () => "étape 2 : tick suivant attendu, partie " + Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null; }
            var bande = toile.Find(CalquesCarte.BANDE) ?? throw Echec("« " + CalquesCarte.BANDE + " » introuvable"); var fond = (RectTransform)(toile.Find(CalquesCarte.LEGENDE) ?? throw Echec("« " + CalquesCarte.LEGENDE + " » introuvable")); var dits = new List<string>();
            foreach (ModeDeCarte mode in new[] { ModeDeCarte.Puissances, ModeDeCarte.Habitants, ModeDeCarte.Flux }) { // étape 3
                (bande.Find(mode.ToString())?.GetComponent<Button>() ?? throw Echec("bouton « " + CalquesCarte.BANDE + "/" + mode + " » introuvable")).onClick.Invoke();
                string Attendue() => mode == ModeDeCarte.Puissances ? CalquesCarte.LegendeDuMode(mode, null, true) : mode == ModeDeCarte.Habitants ? (cabinet.Partie.Monde?.Presente == true ? CalquesCarte.LegendeDuMode(mode, new RepartitionHabitants(cabinet.Partie.Monde.Donnees.Monde)) : null) : CalquesCarte.FLUX;
                for (var e = Lot690.Jusqua(() => calques.Mode == mode && (mode != ModeDeCarte.Puissances || lieux.Peint) && Pret() && calques.Legende.text == Attendue(), () => "étape 3 : mode " + calques.Mode + ", lieux " + (lieux.Peint ? "peints" : "non peints") + ", légende « " + Ligne(calques.Legende.text) + " », attendu « " + Ligne(Attendue()) + " »"); e.MoveNext();) yield return null;
                string attendue = Attendue(); // dans la même image, sans yield
                if (mode == ModeDeCarte.Flux && Drapeau(DEUX)) { var copie = UnityEngine.Object.Instantiate(fond, toile); copie.name = FLOTTANTES[0]; copie.anchoredPosition = ANCIENNE; }
                if (mode == ModeDeCarte.Flux && Drapeau(REMONTER)) fond.anchoredPosition = ANCIENNE;
                Controler(mode.ToString(), attendue); dits.Add(mode + " « " + Ligne(attendue) + " » " + Lignes(attendue) + " lignes");
            }
            if (Drapeau(MUET)) (bande.Find("Flux/Repère fleche") ?? throw Echec("« Flux/Repère fleche » introuvable")).gameObject.SetActive(false); Icones(); // étape 4, dans la même image
            for (int i = 0; i < 10; i++) yield return null; Controler("Flux", CalquesCarte.FLUX); // étape 5
            if (toile.Find(BULLE) is Transform ouverte && ouverte.gameObject.activeInHierarchy) throw Echec("étape 5 : infobulle ouverte : « " + Ligne(ouverte.GetComponentInChildren<Text>(true)?.text) + " »");
            Transform racine = carte.transform.Find(FlechesDeCarte.RACINE); if (racine == null || !racine.Cast<Transform>().Any(f => f.gameObject.activeInHierarchy)) throw Echec("étape 5 : aucune flèche active dans « " + FlechesDeCarte.RACINE + " »");
            Debug.Log("CAPTURE_965 " + string.Join(" · ", dits) + " · tick " + N(tickMonde) + " · " + textes.Length + " textes inchangés"); // étape 6
        }
        // L'état présent, dans la même image : la première faute lève l'erreur.
        static void Controler(string mode, string attendue) {
            var legendes = toile.Cast<Transform>().Where(t => t.gameObject.activeInHierarchy && t.name != BULLE && (t.name == CalquesCarte.LEGENDE || FLOTTANTES.Contains(t.name) || t.GetComponentsInChildren<Text>(false).Any(x => x.isActiveAndEnabled && x.text == attendue))).Select(t => t.name).ToArray(); // 1. une seule légende
            if (legendes.Length != 1 || legendes[0] != CalquesCarte.LEGENDE) throw Echec("deux légendes visibles en mode " + mode + " : " + (legendes.Length == 0 ? "(aucune)" : string.Join(", ", legendes.Select(n => "« " + n + " »"))));
            Text legende = calques.Legende; var fond = (RectTransform)toile.Find(CalquesCarte.LEGENDE); var bande = (RectTransform)toile.Find(CalquesCarte.BANDE); // 2. entière, à sa place
            if (legende.text != attendue) throw Echec("légende « " + Ligne(legende.text) + " » en mode " + mode + ", attendu « " + Ligne(attendue) + " »");
            int lignes = Lignes(attendue); if (lignes > CalquesCarte.LIGNES_MAX) throw Echec("légende de " + lignes + " lignes en mode " + mode + " : « " + Ligne(attendue) + " »");
            if (legende.preferredHeight > legende.rectTransform.rect.height + 1f) throw Echec("légende coupée en mode " + mode + " : " + legende.preferredHeight + " px de texte pour " + legende.rectTransform.rect.height + " px"); Lot690.DansLeChamp(camera, legende);
            foreach (var zone in new[] { fond, bande }) { Rect r = Ecran(camera, zone); if (!Dans(r)) throw Echec("« " + zone.name + " » hors de l'image en mode " + mode + " : " + r + " dans " + camera.pixelWidth + " × " + camera.pixelHeight); }
            var panneaux = toile.Cast<Transform>().OfType<RectTransform>().Where(t => t.GetComponent<Image>() is Image i && i.raycastTarget && !EXCLUS.Contains(t.name)).ToArray(); // 3. sur aucun panneau, ouvert ou fermé
            foreach (var zone in new[] { fond, bande }) { Rect r = Ecran(camera, zone); var sous = panneaux.Where(p => r.Overlaps(Ecran(camera, p))).Select(p => "« " + p.name + " »").ToArray(); if (sous.Length > 0) throw Echec("« " + zone.name + " » recouvre " + string.Join(", ", sous) + " en mode " + mode); }
            if (!Feuillet().gameObject.activeInHierarchy) throw Echec("feuillet « " + FEUILLET + " » fermé en mode " + mode);
            var changes = new List<string>(); HorlogeLue lue = horloge.Lue; long monde = cabinet.Partie.Monde.Donnees.Monde.Tick; string[] lus = Textes(); // 4. aucun nombre servi ne bouge, le tick d'abord
            if (lue.Tick != tickHorloge) changes.Add("tick de l'horloge " + N(tickHorloge) + " → " + N(lue.Tick)); if (monde != tickMonde) changes.Add("tick du monde lu " + N(tickMonde) + " → " + N(monde));
            if (lue.JoursParSeconde != vitesse) changes.Add("jours par seconde " + vitesse.ToString("R", CultureInfo.InvariantCulture) + " → " + lue.JoursParSeconde.ToString("R", CultureInfo.InvariantCulture));
            if (lus.Length != textes.Length) changes.Add(textes.Length + " textes → " + lus.Length); else for (int i = 0; i < lus.Length; i++) if (lus[i] != textes[i]) changes.Add("« " + Ligne(textes[i]) + " » → « " + Ligne(lus[i]) + " »");
            if (changes.Count > 0) throw Echec("nombre servi changé au changement de mode " + mode + " : " + string.Join(", ", changes));
        }
        // Chaque commande de la bande : son icône, sa phrase, son infobulle entière dans l'image.
        static void Icones() {
            Canvas canvas = toile.GetComponent<Canvas>(); Transform bande = toile.Find(CalquesCarte.BANDE);
            foreach (var (mode, motif) in new[] { ("Puissances", "banniere"), ("Habitants", "foule"), ("Flux", "fleche") }) {
                var commande = (RectTransform)(bande.Find(mode) ?? throw Echec("commande « " + mode + " » introuvable")); var repere = commande.Find("Repère " + motif); if (repere == null || !repere.gameObject.activeInHierarchy) throw Echec("icône absente : " + mode);
                string phrase = commande.GetComponent<Infobulle>()?.Phrase; if (string.IsNullOrWhiteSpace(phrase) || phrase == mode) throw Echec("commande « " + mode + " » sans phrase : « " + Ligne(phrase) + " »");
                if ((TexteDuMonde.Interdit(phrase) ?? TexteDuMonde.SansUnite(phrase)) is string mot) throw Echec("« " + mot + " » refusé dans la phrase de « " + mode + " » : « " + Ligne(phrase) + " »");
                RectTransform feuillet = Infobulle.Montrer(canvas, phrase, Ecran(camera, commande).center); Text ecrit = feuillet.GetComponentInChildren<Text>(true); Rect cadre = Ecran(camera, feuillet);
                if (!feuillet.gameObject.activeInHierarchy || ecrit == null || ecrit.text != phrase || !Dans(cadre)) throw Echec("infobulle de « " + mode + " » : « " + Ligne(ecrit?.text) + " » " + (feuillet.gameObject.activeInHierarchy ? "en " + cadre : "cachée"));
                Infobulle.Cacher(canvas);
            }
        } } }
