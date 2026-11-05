using System; using System.Collections; using System.Globalization; using System.Linq; using Forge.Interface; using Forge.Pont; using UnityEngine; using UnityEngine.UI;
namespace ForgeLocal3D.Captures {
    // Lot 1001 : la barre du haut dit la maison de Mistra, sa part et son grenier, lus aux comptes servis au tick du monde lu.
    // La photo du lot 658 (Mistra, 60 %, trente jours, le feuillet ouvert), puis la barre jugée contre des comptes relus à part.
    // Contre-épreuve : `-forge1001Avance` pousse un tick avant la relecture : la barre est restée au tick d'avant, le scénario échoue.
    static class Lot1001 {
        const string AVANCE = "-forge1001Avance", BARRE = "FORGE · Le cabinet/Lecture de la maison…", ATTENTE = "Comptes en attente du monde", PART = "Prélèvement : 60 %"; const int IMAGES = 10;
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");
        static InvalidOperationException Echec(string cause) => new InvalidOperationException(cause); static string N(long? v) => v == null ? "non servi" : v.Value.ToString(CultureInfo.InvariantCulture);
        static CabinetDeCarte cabinet; static HorlogeDeCarte horloge; static Text barre; static int port;
        static bool Pret() { var p = cabinet.Partie; var c = p.Comptes; return !p.Occupee && !horloge.RequeteEnVol && p.Monde?.Presente == true && c != null && c.Presente && c.Donnees.Tick == p.Monde.Donnees.Monde.Tick
            && horloge.Lue != null && horloge.Lue.Tick == c.Donnees.Tick && barre.text != ATTENTE; } // l'horloge a presque toujours une lecture en vol : elle n'est exigée prête qu'à l'instant de juger
        [ScenarioDeCapture(1001, "barre-de-mistra")] static IEnumerator BarreDeMistra(Camera camera) {
            for (var e = Lot658.FlechesDuSiege(camera); e.MoveNext();) yield return null; CarteDessinee carte = Lot658.carte; Transform toile = Lot658.toile; port = carte.port; // étape 1
            cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("étape 1 : pas de CabinetDeCarte"); horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("étape 1 : pas d'horloge");
            barre = toile.Find(BARRE)?.GetComponent<Text>(); if (barre == null || !barre.isActiveAndEnabled) throw Echec("barre introuvable");
            for (var e = Lot690.Jusqua(Pret, () => "étape 2 : partie " + Lot690.Dire(cabinet.Partie) + ", comptes " + Dire(cabinet.Partie.Comptes) + ", horloge " + (horloge.Lue == null ? "non lue" : "au tick " + N(horloge.Lue.Tick)) + ", barre « " + barre.text + " »"); e.MoveNext();) yield return null; // étape 2
            if (Environment.GetCommandLineArgs().Contains(AVANCE)) { var un = Lot690.PousserTick(port).Result; if (un.statut != 200) throw Echec("tick " + un.corps); } // étape 3, dans la même image, sans yield
            string id = cabinet.Partie.Monde.Donnees.MaisonDuJoueur; long? servi = Juger(camera, id);
            for (int i = 0; i < IMAGES; i++) yield return null; servi = Juger(camera, id); // étape 4
            Debug.Log("CAPTURE_1001 barre « " + barre.text + " » au tick " + N(cabinet.Partie.Comptes.Donnees.Tick) + ", comptes servis au tick " + N(servi)); // étape 5
        }
        static string Dire(Lecture<ComptesDeMaison> c) => c == null ? "non lus" : !c.Presente ? "absents : " + c.Absence : "au tick " + N(c.Donnees.Tick);
        // Relit les comptes de la maison du joueur et juge la barre contre eux, dans la même image : la première faute lève l'erreur.
        static long? Juger(Camera camera, string id) {
            Lecture<ComptesDeMaison> lus; using (var client = new ClientMaison(port, TimeSpan.FromSeconds(10))) lus = client.LireComptes(id);
            if (!lus.Presente) throw Echec("comptes de « " + id + " » absents : " + lus.Absence);
            long? lue = cabinet.Partie.Comptes?.Donnees?.Tick, servi = lus.Donnees.Tick;
            if (servi == null || lue != servi) throw Echec("barre lue au tick " + N(lue) + ", comptes servis au tick " + N(servi));
            string texte = barre.text, attendu = Attendu(lus.Donnees);
            if (texte != attendu || !texte.Contains(PART)) throw Echec("barre « " + texte + " » ≠ comptes « " + attendu + " »");
            if ((TexteDuMonde.Interdit(texte, id) ?? TexteDuMonde.SansUnite(texte)) is string mot) throw Echec("« " + mot + " » refusé dans la barre « " + texte + " »");
            Lot690.DansLeChamp(camera, barre); return servi;
        }
        // Le texte que la barre doit montrer, écrit ici sans CabinetDeCarte.Barre ni DossierMaison.
        static string Attendu(ComptesDeMaison c) {
            string Raison(string cle) => c.Maison.Absents.TryGetValue(cle, out string r) ? r : "sans raison";
            string nom = c.Maison.Nom ?? throw Echec("maison sans nom servi : " + Raison("nom"));
            double part = c.Part ?? throw Echec("part absente : " + Raison("part"));
            var grenier = c.Grenier ?? throw Echec("grenier absent : " + Raison("grenier"));
            var panier = grenier.Keys.OrderBy(k => k, StringComparer.Ordinal).Select(k => k + " : " + TexteDuMonde.Masse(grenier[k])).ToArray();
            return nom + " · Prélèvement : " + (part * 100).ToString("0.##", Fr) + " % · Grenier : " + (panier.Length == 0 ? "vide" : string.Join(" · ", panier));
        }
    } }
