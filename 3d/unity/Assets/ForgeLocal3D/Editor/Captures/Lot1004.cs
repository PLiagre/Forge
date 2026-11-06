using System; using System.Collections; using System.Collections.Generic; using System.Globalization; using System.Linq; using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 1004 : la preuve de la barre. Mistra en pause, 60 % de part, trente jours (le parcours du lot 658) : la barre dit la date, le grenier et la part servis au même tick,
    // chaque commande de l'ancien panneau garde sa place, aucun dossier ne recouvre la barre et, à 1280 × 720, rien n'y est coupé. Les jugements sont écrits ici.
    // Contre-épreuves : `-forge1004Avance` pousse un tick avant de juger, `-forge1004Perdre` détruit « Autres maisons », `-forge1004Recouvrir` monte un feuillet
    // sur la barre, `-forge1004Couper` rétrécit la barre à 600 px : chacune fait échouer le scénario.
    static class Lot1004 {
        const string AVANCE = "-forge1004Avance", PERDRE = "-forge1004Perdre", RECOUVRIR = "-forge1004Recouvrir", COUPER = "-forge1004Couper", BANDEAU = "FORGE · Le cabinet", BARRE = BANDEAU + "/Lecture de la maison…", DATE = BANDEAU + "/Lecture de la date…";
        const string ATTENTE = "Comptes en attente du monde", PART = "Prélèvement : 60 %", NOM = "Parcourir le monde", MENU = "Menu", AUTRES = "Autres maisons", COMPTES = "Terres et comptes", VOISINS = "Les autres maisons", MENU_OUVERT = "Menu du cabinet"; const int IMAGES_DE_POSE = 10, LARGEUR = 1280, HAUTEUR = 720;
        static readonly string[] MODES = { "Puissances", "Habitants", "Flux" }, DOSSIERS = { COMPTES, AUTRES }, TEMPS = { "Ralentir", "Pause / Reprendre", "Accélérer" }, PANNEAUX = { COMPTES, VOISINS, MENU_OUVERT };
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR"), Inv = CultureInfo.InvariantCulture;
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string N(long? v) => v == null ? "non servi" : v.Value.ToString(Inv); static string F(float v) => v.ToString("0.#", Inv);
        static string Ecran(Vector2 p) => "(" + Mathf.RoundToInt(p.x) + ", " + Mathf.RoundToInt(p.y) + ")"; static string Ecran(Rect r) => "[" + Ecran(r.min) + " – " + Ecran(r.max) + "]"; static string Ligne(string t) => t.Replace("\r", "").Replace("\n", " | ");
        static string Chemin(Transform t) => t.parent == null ? t.name : Chemin(t.parent) + "/" + t.name; static bool Dans(Rect r, Rect cadre) => r.xMin >= cadre.xMin - .5f && r.yMin >= cadre.yMin - .5f && r.xMax <= cadre.xMax + .5f && r.yMax <= cadre.yMax + .5f;
        static Button Commande(string nom) => bandeau.Cast<Transform>().Where(t => t.name == nom).Select(t => t.GetComponent<Button>()).FirstOrDefault(b => b != null); // Find lirait « / » comme un chemin
        static Rect Reduit(Rect r) => Rect.MinMaxRect(r.xMin + .5f, r.yMin + .5f, r.xMax - .5f, r.yMax - .5f); static bool Drapeau(string d) => Environment.GetCommandLineArgs().Contains(d);
        static Rect Coins(Camera camera, Transform cadre) { var c = new Vector3[4]; ((RectTransform)cadre).GetWorldCorners(c); return Ecrin(c.Select(v => RectTransformUtility.WorldToScreenPoint(camera, v))); }
        static Rect Ecrin(IEnumerable<Vector2> points) { var p = points.ToArray(); return Rect.MinMaxRect(p.Min(v => v.x), p.Min(v => v.y), p.Max(v => v.x), p.Max(v => v.y)); }
        static CarteDessinee carte; static Transform toile, bandeau, bande, conteneur; static CabinetDeCarte cabinet; static HorlogeDeCarte horloge; static Text barre, date;
        static bool Pret() { var p = cabinet.Partie; var c = p.Comptes; return !p.Occupee && !horloge.RequeteEnVol && p.Monde?.Presente == true && c != null && c.Presente && c.Donnees.Tick == p.Monde.Donnees.Monde.Tick
            && horloge.Lue != null && horloge.Lue.Tick == c.Donnees.Tick && barre.text != ATTENTE; }
        [ScenarioDeCapture(1004, "barre-en-pause")] static IEnumerator BarreEnPause(Camera camera) {
            for (var e = Lot658.FlechesDuSiege(camera); e.MoveNext();) yield return null; carte = Lot658.carte; toile = Lot658.toile; // étape 1, comme Lot1001
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte"); horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : pas d'horloge");
            barre = toile.Find(BARRE)?.GetComponent<Text>(); if (barre == null || !barre.isActiveAndEnabled) throw Echec("barre introuvable"); date = toile.Find(DATE)?.GetComponent<Text>(); if (date == null || !date.isActiveAndEnabled) throw Echec("date introuvable");
            bandeau = toile.Find(BANDEAU); bande = toile.Find(CalquesCarte.BANDE) ?? throw Echec("étape 1 : « " + CalquesCarte.BANDE + " » introuvable"); conteneur = toile.Find(BANDEAU + "/" + CabinetDeCarte.DOSSIERS) ?? throw Echec("étape 1 : « " + CabinetDeCarte.DOSSIERS + " » introuvable");
            if (Drapeau(PERDRE) && conteneur.Find(AUTRES) is Transform perdu) UnityEngine.Object.DestroyImmediate(perdu.gameObject); // étape 2 : la contre-épreuve perd une commande
            Button menu = Places("étape 2");
            camera.rect = new Rect(0, 0, 1, 1); camera.targetTexture = new RenderTexture(LARGEUR, HAUTEUR, 24); camera.ResetAspect(); // étape 3 : 1280 × 720
            Canvas cab = toile.GetComponent<Canvas>(); cab.renderMode = RenderMode.ScreenSpaceCamera; cab.worldCamera = camera; cab.planeDistance = camera.nearClipPlane + 0.2f; yield return null; Canvas.ForceUpdateCanvases();
            if (Drapeau(COUPER)) barre.rectTransform.sizeDelta = new Vector2(Mathf.Min(600, barre.preferredWidth / 2), 26); // la barre de Mistra tient en moins de 600 : la moitié de son texte la coupe toujours
            Button voisins = conteneur.Find(AUTRES).GetComponent<Button>(); voisins.onClick.Invoke(); menu.onClick.Invoke(); yield return null; Canvas.ForceUpdateCanvases(); // étape 4
            if (Drapeau(RECOUVRIR)) ((RectTransform)Panneau(VOISINS, "étape 4")).anchoredPosition = new Vector2(24, -60);
            Ouverts("étape 4", PANNEAUX); Recouvre(camera, "étape 4, dossiers ouverts");
            voisins.onClick.Invoke(); menu.onClick.Invoke(); yield return null; Canvas.ForceUpdateCanvases(); Ouverts("étape 4, dossiers refermés", COMPTES); Recouvre(camera, "étape 4, dossiers refermés");
            for (var e = Lot690.Jusqua(Pret, () => "étape 5 : partie " + Lot690.Dire(cabinet.Partie) + ", comptes au tick " + N(cabinet.Partie.Comptes?.Donnees?.Tick) + ", horloge " + (horloge.Lue == null ? "non lue" : "au tick " + N(horloge.Lue.Tick)) + ", barre « " + barre.text + " »"); e.MoveNext();) yield return null;
            if (Drapeau(AVANCE)) { var un = Lot690.PousserTick(carte.port).Result; if (un.statut != 200) throw Echec("étape 6 : tick " + un.corps); } // étape 6, dans la même image, sans yield
            string id = cabinet.Partie.Monde.Donnees.MaisonDuJoueur; long? servi = Juger(camera, id, menu, "étape 6");
            for (int i = 0; i < IMAGES_DE_POSE; i++) yield return null; Places("étape 7, après la pose"); servi = Juger(camera, id, menu, "étape 7, après la pose"); Recouvre(camera, "étape 7, après la pose"); // étape 7
            Debug.Log("CAPTURE_1004 barre « " + Ligne(barre.text) + " » · date « " + Ligne(date.text) + " » au tick " + N(cabinet.Partie.Comptes.Donnees.Tick) + ", comptes servis au tick " + N(servi) + " · commandes : " + string.Join(", ", MODES)
                + " dans la bande ; " + string.Join(", ", DOSSIERS) + " dans la barre ; " + MENU + " · aucun panneau sur la barre · rien de coupé à " + LARGEUR + " × " + HAUTEUR); // étape 8
        }
        // Étape 2 : l'ancien panneau a disparu, inactifs compris, et chaque commande qu'il portait est un seul bouton, actif, à sa place ; rend le Menu.
        static Button Places(string quand) {
            Transform reste = UnityEngine.Object.FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault(t => t.name == NOM); if (reste != null) throw Echec(quand + " : panneau « " + NOM + " » encore là : " + Chemin(reste));
            Button[] boutons = toile.GetComponentsInChildren<Button>(true);
            Button Seul(string nom, Transform parent) { Button[] t = boutons.Where(b => b.name == nom).ToArray(); if (t.Length == 0) throw Echec(quand + " : commande « " + nom + " » perdue : 0 bouton dans la toile");
                if (t.Length > 1) throw Echec(quand + " : commande « " + nom + " » en double : " + t.Length + " boutons, sous " + string.Join(", ", t.Select(b => "« " + Chemin(b.transform.parent) + " »")));
                if (t[0].transform.parent != parent || !t[0].gameObject.activeInHierarchy) throw Echec(quand + " : commande « " + nom + " » hors de sa place : sous « " + Chemin(t[0].transform.parent) + " »" + (t[0].gameObject.activeInHierarchy ? "" : ", cachée") + ", attendue active sous « " + Chemin(parent) + " »"); return t[0]; }
            foreach (string nom in MODES) Seul(nom, bande); foreach (string nom in DOSSIERS) Seul(nom, conteneur); Button menu = Seul(MENU, toile); string phrase = menu.GetComponent<Infobulle>()?.Phrase;
            if (phrase == null || !phrase.EndsWith(CabinetDeCarte.AIDE, StringComparison.Ordinal)) throw Echec(quand + " : la phrase du Menu « " + phrase + " » ne finit pas par l'aide « " + CabinetDeCarte.AIDE + " »"); return menu;
        }
        // Les panneaux du socle sont les enfants directs de la toile qui portent un « Filet » ; le bandeau en est un, jugé à part.
        static Transform Panneau(string nom, string quand) { Transform[] t = toile.Cast<Transform>().Where(p => p.name == nom && p.Find("Filet") != null).ToArray(); if (t.Length != 1) throw Echec(quand + " : " + t.Length + " panneau(x) « " + nom + " » dans la toile, attendu un seul"); return t[0]; }
        static void Ouverts(string quand, params string[] ouverts) { foreach (string nom in PANNEAUX) { bool actif = Panneau(nom, quand).gameObject.activeInHierarchy; if (actif != ouverts.Contains(nom)) throw Echec(quand + " : « " + nom + " » " + (actif ? "ouvert" : "fermé")); } }
        static void Recouvre(Camera camera, string quand) { Rect cadre = Coins(camera, bandeau), reduit = Reduit(cadre);
            foreach (Transform panneau in toile.Cast<Transform>().Where(t => t != bandeau && t.gameObject.activeInHierarchy && t.Find("Filet") != null)) { Rect r = Coins(camera, panneau); if (r.Overlaps(reduit)) throw Echec(quand + " : « " + panneau.name + " » recouvre la barre : " + Ecran(r) + " sur " + Ecran(cadre)); } }
        // Étape 6 : relit les comptes de la maison du joueur et juge la barre, la date et leurs cadres contre eux, dans la même image ; la première faute lève l'erreur.
        static long? Juger(Camera camera, string id, Button menu, string quand) {
            Lecture<ComptesDeMaison> lus; using (var client = new ClientMaison(carte.port, TimeSpan.FromSeconds(10))) lus = client.LireComptes(id);
            if (!lus.Presente) throw Echec(quand + " : comptes de « " + id + " » absents : " + lus.Absence);
            long? lue = cabinet.Partie.Comptes?.Donnees?.Tick, heure = horloge.Lue?.Tick, servi = lus.Donnees.Tick;
            if (servi == null || lue != servi || heure != servi) throw Echec(quand + " : barre lue au tick " + N(lue) + " (horloge au tick " + N(heure) + "), comptes servis au tick " + N(servi));
            string texte = barre.text, attendu = Attendu(lus.Donnees); if (texte != attendu || !texte.Contains(PART)) throw Echec(quand + " : barre « " + texte + " » ≠ comptes « " + attendu + " »");
            string decrite = HorlogeDeCarte.Decrire(horloge.Lue), pause = Commande(TEMPS[1])?.GetComponentInChildren<Text>()?.text ?? "(introuvable)";
            if (horloge.Lue.JoursParSeconde != 0) throw Echec(quand + " : maison pas en pause : " + horloge.Lue.JoursParSeconde.ToString(Inv) + " jour(s) par seconde");
            if (date.text != decrite || !date.text.EndsWith("\nEn pause", StringComparison.Ordinal)) throw Echec(quand + " : maison pas en pause : date « " + Ligne(date.text) + " », horloge « " + Ligne(decrite) + " »");
            if (pause != "Reprendre") throw Echec(quand + " : maison pas en pause : le bouton « " + TEMPS[1] + " » dit « " + pause + " »");
            foreach (string dit in new[] { texte, date.text }) if ((TexteDuMonde.Interdit(dit, id) ?? TexteDuMonde.SansUnite(dit)) is string mot) throw Echec(quand + " : « " + mot + " » refusé dans « " + Ligne(dit) + " »");
            Coupes(camera, menu, quand); return servi;
        }
        // Le texte que la barre doit montrer, écrit ici sans CabinetDeCarte.Barre ni DossierMaison, comme Lot1001.
        static string Attendu(ComptesDeMaison c) {
            string Raison(string cle) => c.Maison.Absents.TryGetValue(cle, out string r) ? r : "sans raison";
            string nom = c.Maison.Nom ?? throw Echec("maison sans nom servi : " + Raison("nom")); double part = c.Part ?? throw Echec("part absente : " + Raison("part")); var grenier = c.Grenier ?? throw Echec("grenier absent : " + Raison("grenier"));
            var panier = grenier.Keys.OrderBy(k => k, StringComparer.Ordinal).Select(k => k + " : " + TexteDuMonde.Masse(grenier[k])).ToArray();
            return nom + " · Prélèvement : " + (part * 100).ToString("0.##", Fr) + " % · Grenier : " + (panier.Length == 0 ? "vide" : string.Join(" · ", panier));
        }
        // À 1280 × 720 : chaque texte actif du bandeau, et celui du Menu, tient dans son cadre ; ses glyphes tiennent dans l'image et le bandeau ; ceux du titre, de la date
        // et de la barre ne se touchent pas et ne touchent aucun bouton de la barre, qui tiennent eux aussi dans le bandeau et l'image. Tout en coins d'écran, à 0,5 px près.
        static void Coupes(Camera camera, Button menu, string quand) {
            Canvas.ForceUpdateCanvases(); Rect image = camera.pixelRect, cadre = Coins(camera, bandeau);
            InvalidOperationException Coupe(string nom, string mesure) => Echec(quand + " : texte coupé dans la barre : « " + nom + " » " + mesure);
            Text titre = bandeau.Find(BANDEAU)?.GetComponent<Text>(), libelle = menu.GetComponentInChildren<Text>(); if (titre == null || !titre.isActiveAndEnabled) throw Coupe(BANDEAU, "titre introuvable"); if (libelle == null || !libelle.isActiveAndEnabled) throw Coupe(MENU, "sans libellé");
            Text[] textes = bandeau.GetComponentsInChildren<Text>().Where(t => t.isActiveAndEnabled).Append(libelle).ToArray(); var glyphes = new Dictionary<Text, Rect>();
            foreach (string nom in TEMPS) if (!textes.Any(t => t.transform.parent.name == nom)) throw Coupe(nom, "sans libellé actif");
            foreach (Text t in textes) { Rect propre = t.rectTransform.rect;
                if (t.preferredWidth > propre.width + .5f || t.preferredHeight > propre.height + .5f) throw Coupe(t.name, "texte de " + F(t.preferredWidth) + " × " + F(t.preferredHeight) + " pour un cadre de " + F(propre.width) + " × " + F(propre.height));
                IList<UIVertex> v = t.cachedTextGenerator.verts; if (v.Count == 0) throw Coupe(t.name, "sans un glyphe dessiné"); float ppu = t.pixelsPerUnit;
                Rect g = Ecrin(v.Select(s => RectTransformUtility.WorldToScreenPoint(camera, t.rectTransform.TransformPoint(s.position / ppu)))); // le repère du Text, puis l'écran
                if (!Dans(g, image) || !Dans(g, cadre)) throw Coupe(t.name, "glyphes " + Ecran(g) + " hors de l'image " + Ecran(image) + " ou du bandeau " + Ecran(cadre)); glyphes[t] = g; }
            Button[] boutons = new[] { menu }.Concat(conteneur.GetComponentsInChildren<Button>(true)).Concat(TEMPS.Select(n => Commande(n) ?? throw Coupe(n, "bouton introuvable"))).ToArray();
            if (boutons.Length != 6) throw Coupe(CabinetDeCarte.DOSSIERS, (boutons.Length - 4) + " icône(s), attendu deux");
            foreach (Button b in boutons) { Rect r = Coins(camera, b.transform); if (!Dans(r, cadre) || !Dans(r, image)) throw Coupe(b.name, "bouton " + Ecran(r) + " hors du bandeau " + Ecran(cadre) + " ou de l'image " + Ecran(image)); }
            Text[] trio = { titre, date, barre };
            for (int i = 0; i < trio.Length; i++) { Rect a = Reduit(glyphes[trio[i]]);
                for (int j = i + 1; j < trio.Length; j++) if (a.Overlaps(glyphes[trio[j]])) throw Coupe(trio[i].name, "glyphes " + Ecran(glyphes[trio[i]]) + " sur « " + trio[j].name + " » " + Ecran(glyphes[trio[j]]));
                foreach (Button b in boutons) { Rect r = Coins(camera, b.transform); if (a.Overlaps(r)) throw Coupe(trio[i].name, "glyphes " + Ecran(glyphes[trio[i]]) + " sur le bouton « " + b.name + " » " + Ecran(r)); } }
        }
    } }
