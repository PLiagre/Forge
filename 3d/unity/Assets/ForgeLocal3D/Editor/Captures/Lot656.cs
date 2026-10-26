using System;
using System.Collections;
using System.Globalization;
using System.Linq;
using System.Threading.Tasks;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;
namespace ForgeLocal3D.Captures
{
    // Lot 656 : curseur à 25 %, puis grenier refusé. `-forge656SansConfirmation` saute seulement la confirmation de la part.
    static class Lot656
    {
        const string SIEGE = "Mistra", SANS = "-forge656SansConfirmation", NOURRITURE = "nourriture", CONFIRMER = "Confirmer l\u2019ordre"; const double ATTENTE_S = 15; const int IMAGES = 10;
        static readonly CultureInfo Inv = CultureInfo.InvariantCulture;
        static CarteDessinee carte; static Transform toile, racine; static CommandesMaison commandes; static string maison; static int port; static long nRecu;
        static string N(long v) => v.ToString(Inv);
        static string Ligne(string t) => t == null ? "(aucun)" : t.Replace("\r", "").Replace("\n", " | ");
        static InvalidOperationException Echec(string c) => new InvalidOperationException(c);

        [ScenarioDeCapture(656, "01-part-posee")] static IEnumerator PartPosee(Camera camera)
        {
            var ouverte = new Lot549.CarteOuverte(); for (var e = Lot549.Ouvrir(camera, ouverte); e.MoveNext();) yield return null;
            carte = ouverte.Carte; port = carte.port;
            var cabinet = carte.GetComponent<CabinetDeCarte>() ?? throw Echec("la carte n'a pas de CabinetDeCarte");
            toile = carte.transform.Find("Cabinet"); if (toile == null || !toile.gameObject.activeInHierarchy) throw Echec("toile inactive");
            commandes = carte.GetComponent<CommandesMaison>() ?? throw Echec("pas de CommandesMaison"); racine = toile.Find("Votre maison/Commandes de maison") ?? throw Echec("commandes introuvables");
            var horloge = carte.GetComponent<HorlogeDeCarte>() ?? throw Echec("pas d'horloge");
            for (var e = Jusqua(() => Lot690.LecturePrete(cabinet.Partie), () => Lot690.Dire(cabinet.Partie)); e.MoveNext();) yield return null;
            for (var e = Jusqua(() => horloge.Lue != null && horloge.Lue.JoursParSeconde == 0, () => "horloge : " + (horloge.Absence ?? horloge.TexteAffiche)); e.MoveNext();) yield return null;
            var partie = cabinet.Partie; var mistra = partie.Departs.Donnees.Fiches.Where(f => f.Siege.Nom == SIEGE).ToArray();
            if (mistra.Length != 1) throw Echec(mistra.Length + " départs au siège " + SIEGE);
            long tick = partie.Monde.Donnees.Monde.Tick; var choix = partie.Choisir(mistra[0].Id); for (var e = Lot690.Attendre(choix, "choix"); e.MoveNext();) yield return null;
            if (partie.Recu == null || !partie.Recu.Acceptee || partie.Recu.AppliqueeAuTick != tick) throw Echec("reçu du choix refusé");
            var un = Lot690.PousserTick(port); for (var e = Lot690.Attendre(un, "tick"); e.MoveNext();) yield return null; if (un.Result.statut != 200) throw Echec("tick " + un.Result.statut + " " + un.Result.corps);
            for (var e = Jusqua(() => Bouton("Prélèvement").interactable && partie.Maison?.Presente == true && partie.Maison.Donnees.Siege.Nom == SIEGE && partie.Monde.Donnees.MaisonDuJoueur == partie.Maison.Donnees.Id && Releve() != null, () => "comptes indisponibles : " + Ligne(Releve()?.text)); e.MoveNext();) yield return null;
            maison = partie.Monde.Donnees.MaisonDuJoueur; var avant = Comptes(maison); for (var e = Lot690.Attendre(avant, "comptes"); e.MoveNext();) yield return null;
            if (!avant.Result.Presente || avant.Result.Donnees.Part == null || Math.Abs(avant.Result.Donnees.Part.Value - 0.25) <= 1e-7) throw Echec("part ancienne " + avant.Result.Donnees?.Part + " " + avant.Result.Absence);
            double ancienne = avant.Result.Donnees.Part.Value; Bouton("Prélèvement").onClick.Invoke(); yield return null;
            var curseur = racine.GetComponentInChildren<Slider>(true); if (curseur == null || !curseur.gameObject.activeInHierarchy) throw Echec("curseur invisible");
            curseur.value = 25; yield return null; var saisie = racine.GetComponentInChildren<InputField>(true);
            if (Math.Abs(curseur.value - 25f) > 0.01f || saisie == null || saisie.text != "25") throw Echec("curseur " + curseur.value + " saisie " + (saisie == null ? "" : saisie.text));
            Bouton("Préparer").onClick.Invoke(); yield return null; if (!Environment.GetCommandLineArgs().Contains(SANS)) Bouton(CONFIRMER).onClick.Invoke();
            for (var e = Jusqua(() => commandes.Ordre.Recu != null && commandes.Ordre.Recu.Acceptee && commandes.MessageAffiche.Contains("après le tick " + commandes.Ordre.Recu.AppliqueeAuTick.Value.ToString(Inv)), () => "reçu absent, part " + ancienne.ToString(Inv) + " « " + Ligne(commandes.MessageAffiche) + " »"); e.MoveNext();) yield return null;
            nRecu = commandes.Ordre.Recu.AppliqueeAuTick.Value; var pendant = Comptes(maison); var mondeP = Lot690.LireMonde(port); for (var e = Lot690.Attendre(Task.WhenAll(pendant, mondeP), "avant tick"); e.MoveNext();) yield return null;
            if (!pendant.Result.Presente || Math.Abs((pendant.Result.Donnees.Part ?? -1) - ancienne) > 1e-9) throw Echec("part changée avant le tick : " + pendant.Result.Donnees?.Part); Lot690.ExigerMonde(mondeP.Result, nRecu, maison, "avant l'application");
            var deux = Lot690.PousserTick(port); for (var e = Lot690.Attendre(deux, "tick part"); e.MoveNext();) yield return null; if (deux.Result.statut != 200) throw Echec("second tick " + deux.Result.statut + " " + deux.Result.corps);
            for (var e = Jusqua(() => { var r = Releve(); return r != null && r.text.Contains("25 %") && r.text.Contains("tick " + N(nRecu + 1)) && curseur.gameObject.activeInHierarchy && !curseur.interactable && Math.Abs(curseur.value - 25f) < 0.01f && commandes.MessageAffiche.Contains("après le tick " + N(nRecu)); }, () => "relevé « " + Ligne(Releve()?.text) + " » curseur " + curseur.value); e.MoveNext();) yield return null;
            var apres = Comptes(maison); var monde = Lot690.LireMonde(port); for (var e = Lot690.Attendre(Task.WhenAll(apres, monde), "après part"); e.MoveNext();) yield return null;
            Lot690.ExigerMonde(monde.Result, nRecu + 1, maison, "après la part"); if (!apres.Result.Presente || Math.Abs((apres.Result.Donnees.Part ?? -1) - 0.25) > 1e-7) throw Echec("part " + apres.Result.Donnees?.Part + " au tick " + N(nRecu + 1));
            Text legende = racine.GetComponentsInChildren<Text>(true).Single(t => t.text == "25 %"); Text message = Message(), releve = Releve(); string gardeMessage = message.text, gardeReleve = releve.text;
            for (var e = Poser(camera, message, releve, legende, Bouton("Prélèvement").GetComponentInChildren<Text>()); e.MoveNext();) yield return null; if (message.text != gardeMessage || releve.text != gardeReleve || !curseur.gameObject.activeInHierarchy || curseur.interactable) throw Echec("après la pose : « " + Ligne(message.text) + " »");
            Debug.Log("CAPTURE_656 maison " + maison + ", valeur 0.25, N reçu " + N(nRecu) + ", tick relu " + N(monde.Result.Donnees.Monde.Tick));
        }

        [ScenarioDeCapture(656, "02-grenier-refuse")] static IEnumerator GrenierRefuse(Camera camera)
        {
            if (commandes == null || racine == null) throw Echec("le cabinet du premier scénario n'est plus là"); Bouton("Annuler / Retour").onClick.Invoke(); yield return null;
            for (var e = Jusqua(() => Bouton("Ouvrir le grenier").interactable && commandes.Ordre.Recu == null, () => "retour « " + Ligne(commandes.MessageAffiche) + " »"); e.MoveNext();) yield return null;
            var avant = Comptes(maison); var monde = Lot690.LireMonde(port); for (var e = Lot690.Attendre(Task.WhenAll(avant, monde), "grenier"); e.MoveNext();) yield return null;
            if (!avant.Result.Presente || !monde.Result.Presente) throw Echec(avant.Result.Absence ?? monde.Result.Absence);
            var panier = avant.Result.Donnees.Grenier; if (panier == null) throw Echec("grenier déclaré absent");
            double stock = panier.TryGetValue(NOURRITURE, out double nourriture) ? nourriture : 0; long tick = monde.Result.Donnees.Monde.Tick; double? part = avant.Result.Donnees.Part; string demande = Kilos(stock);
            Bouton("Ouvrir le grenier").onClick.Invoke(); yield return null;
            var saisie = racine.GetComponentInChildren<InputField>(true); if (saisie == null || !saisie.gameObject.activeInHierarchy) throw Echec("saisie du grenier invisible");
            saisie.text = demande; Bouton("Préparer").onClick.Invoke(); yield return null; if (commandes.Ordre.Resume == null || !commandes.Ordre.Resume.Contains(demande)) throw Echec("résumé « " + commandes.Ordre.Resume + " »");
            Bouton(CONFIRMER).onClick.Invoke();
            for (var e = Jusqua(() => { var r = commandes.Ordre.Recu; return r != null && r.Statut == 400 && r.Erreur != null && r.Erreur.StartsWith("grenier insuffisant :") && commandes.MessageAffiche.Contains(r.Erreur) && commandes.MessageAffiche.Contains(demande); }, () => "refus « " + Ligne(commandes.MessageAffiche) + " »"); e.MoveNext();) yield return null;
            var apres = Comptes(maison); var mondeApres = Lot690.LireMonde(port); for (var e = Lot690.Attendre(Task.WhenAll(apres, mondeApres), "après refus"); e.MoveNext();) yield return null;
            Lot690.ExigerMonde(mondeApres.Result, tick, maison, "après le refus"); if (!apres.Result.Presente || apres.Result.Donnees.Part != part || !MemePanier(panier, apres.Result.Donnees.Grenier)) throw Echec("le refus a changé tick, part ou panier");
            Text message = Message(); string garde = message.text; for (var e = Poser(camera, message, Releve(), Bouton("Ouvrir le grenier").GetComponentInChildren<Text>()); e.MoveNext();) yield return null;
            if (message.text != garde || !message.text.Contains(commandes.Ordre.Recu.Erreur)) throw Echec("après la pose : « " + Ligne(message.text) + " »");
            Debug.Log("CAPTURE_656 maison " + maison + ", valeur " + demande + " kg, N reçu " + N(nRecu) + ", tick relu " + N(tick) + ", refus " + commandes.Ordre.Recu.Erreur);
        }

        static IEnumerator Poser(Camera camera, params Text[] textes)
        {
            Lot549.Photographier(camera, carte); camera.rect = new Rect(0f, 0f, 1f, 1f); var canvas = toile.GetComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceCamera; canvas.worldCamera = camera; canvas.planeDistance = camera.nearClipPlane + 0.2f;
            yield return null; Canvas.ForceUpdateCanvases(); foreach (var t in textes) Controle(camera, t); for (int i = 0; i < IMAGES; i++) yield return null; foreach (var t in textes) Controle(camera, t);
        }
        static void Controle(Camera camera, Text texte)
        { if (texte == null || !texte.gameObject.activeInHierarchy) throw Echec("contrôle absent"); Lot690.DansLeChamp(camera, texte); if (texte.preferredHeight > texte.rectTransform.rect.height + 1f) throw Echec("texte tronqué : " + Ligne(texte.text)); }
        static IEnumerator Jusqua(Func<bool> fini, Func<string> sinon)
        { for (double fin = Time.realtimeSinceStartupAsDouble + ATTENTE_S; !fini();) { if (Time.realtimeSinceStartupAsDouble > fin) throw Echec(sinon() + " en " + ATTENTE_S.ToString(Inv) + " s"); yield return null; } }
        static Button Bouton(string nom)
        { var trouves = racine.GetComponentsInChildren<Button>(true).Where(b => b.name == nom).ToArray(); if (trouves.Length != 1) throw Echec(trouves.Length + " boutons « " + nom + " »"); return trouves[0]; }
        static Text Releve() => racine.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text != null && t.text.StartsWith("Prélèvement :"));
        static Text Message() => racine.GetComponentsInChildren<Text>(true).FirstOrDefault(t => t.text == commandes.MessageAffiche) ?? throw Echec("message absent : « " + Ligne(commandes.MessageAffiche) + " »");
        static Task<Lecture<ComptesDeMaison>> Comptes(string id) => Task.Run(() => { using (var c = new ClientMaison(port, TimeSpan.FromSeconds(ATTENTE_S))) return c.LireComptes(id); });
        static string Kilos(double stock)
        {
            if (double.IsNaN(stock) || double.IsInfinity(stock) || stock < 0) throw Echec("nourriture illisible : " + stock.ToString(Inv));
            foreach (string format in new[] { "0.########", "0.####", "0.##", "0" }) { string texte = (stock + 1.0).ToString(format, Inv); if (texte.Length <= 18 && double.TryParse(texte, NumberStyles.Float, Inv, out double relu) && relu > stock) return texte; } throw Echec("impossible de demander un kilo de plus que " + stock.ToString(Inv));
        }
        static bool MemePanier(System.Collections.Generic.IReadOnlyDictionary<string, double> a, System.Collections.Generic.IReadOnlyDictionary<string, double> b)
        { if (a == null || b == null || a.Count != b.Count) return false; foreach (var kv in a) if (!b.TryGetValue(kv.Key, out double v) || v != kv.Value) return false; return true; }
    }
}
