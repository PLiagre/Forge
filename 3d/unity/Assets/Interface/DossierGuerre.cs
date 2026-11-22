using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Les intentions de guerre, écrites comme `sim/intentions.py` les attend (`CHAMPS_OBLIGATOIRES`) : les octets que le service
    // reçoit de la main de l'IA comme de la nôtre. La levée se répartit dans l'ordre des lieux servis, chacun jusqu'à sa part servie.
    public static class IntentionsDeGuerre
    {
        static string Chaine(string s) => "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
        static string N(long n) => n.ToString(CultureInfo.InvariantCulture);
        static string Maison(string maison) => !string.IsNullOrWhiteSpace(maison) ? Chaine(maison) : throw new ArgumentException("Maison non confirmée par le monde", nameof(maison));
        public static string Declarer(string maison, string cible) =>
            "{\"type\":\"declarer_guerre\",\"maison\":" + Maison(maison) + ",\"cible\":" + Chaine(cible ?? throw new ArgumentNullException(nameof(cible))) + "}";
        public static string Lever(string maison, IEnumerable<(long cell, long rang, long hommes)> lieux, long vivresKg)
        {
            var liste = lieux.ToList();
            if (liste.Count == 0) throw new ArgumentException("Aucun homme à lever", nameof(lieux));
            if (vivresKg < 0) throw new ArgumentOutOfRangeException(nameof(vivresKg), "des vivres positifs ou nuls attendus");
            return "{\"type\":\"lever_armee\",\"maison\":" + Maison(maison) + ",\"lieux\":[" + string.Join(",", liste.Select(l => "[" + N(l.cell) + "," + N(l.rang) + "," + N(l.hommes) + "]"))
                + "],\"vivres_kg\":" + N(vivresKg) + "}";
        }
        public static string Marcher(string maison, long armee, long cell) =>
            "{\"type\":\"marcher\",\"maison\":" + Maison(maison) + ",\"armee\":" + N(armee) + ",\"cell\":" + N(cell) + ",\"rang\":0}";
        public static string Assieger(string maison, long armee) => "{\"type\":\"assieger\",\"maison\":" + Maison(maison) + ",\"armee\":" + N(armee) + "}";
        public static string Renvoyer(string maison, long armee) => "{\"type\":\"renvoyer_armee\",\"maison\":" + Maison(maison) + ",\"armee\":" + N(armee) + "}";
        // Le plus d'hommes que la levée peut demander : la somme des parts des lieux, au plus les paysans libres servis.
        public static long Maximum(LeveeLue levee) => Math.Min(levee.Lieux.Sum(l => l.HommesMax), levee.Paysans);
        // `hommes` répartis dans l'ordre des lieux servis, chacun jusqu'à sa part ; les lieux qui ne donnent personne sont omis.
        public static List<(long cell, long rang, long hommes)> Repartir(LeveeLue levee, long hommes)
        {
            var lieux = new List<(long, long, long)>(); long reste = Math.Min(hommes, Maximum(levee));
            foreach (var l in levee.Lieux) { long n = Math.Min(l.HommesMax, reste); if (n > 0) { lieux.Add((l.CellId, l.Rang, n)); reste -= n; } }
            return lieux;
        }
    }

    // Le feuillet « La guerre », ouvert par la commande du même nom du panneau « Votre maison » : mes guerres, mes armées, mes prises ;
    // à sa droite, le panneau « Ordres de guerre » avec les cinq ordres, chacun avec son prix et son refus d'avance lus dans le devis
    // servi (`/guerres/ordres`, la terre gardée sur la carte visée). Un ordre se prépare puis se confirme par `OrdreConfirme` : le dépôt
    // `POST /intention` du joueur et de l'IA. Un refus du monde au dépôt s'affiche avec sa raison. Aucun nombre n'est décidé ici.
    public sealed class DossierGuerre : MonoBehaviour
    {
        public const string TITRE = "La guerre", ORDRES = "Ordres de guerre", COMMANDE = "La guerre";
        public const string LEVER = "Lever l'ost", DECLARER = "Déclarer la guerre", MARCHER = "Marcher", ASSIEGER = "Assiéger", RENVOYER = "Renvoyer", SUIVANTE = "Armée suivante";
        public const string CONFIRMER = "Confirmer cet ordre", RETOUR = "Retour aux ordres";
        public const double PERIODE_S = 2;
        const float LARGEUR = 452;
        static readonly TimeSpan DELAI = TimeSpan.FromSeconds(10);

        public Func<string, long?, Lecture<OrdresDeGuerre>> LecteurOrdres;
        public Func<Lecture<GuerresLues>> LecteurGuerres;
        public Func<string, Lecture<MaisonLue>> LecteurMaison;
        public Lecture<OrdresDeGuerre> Ordres { get; private set; }
        public Lecture<GuerresLues> Guerres { get; private set; }
        public OrdreConfirme Ordre { get; private set; }
        public Feuillet Feuillet { get; private set; }
        public RectTransform Panneau { get; private set; }
        public Slider CurseurHommes { get; private set; }
        public Slider CurseurVivres { get; private set; }
        public string TexteAffiche { get; private set; } = "";
        public string EtatAffiche => etat == null ? "" : etat.text;
        public string MessageAffiche => message == null ? "" : message.text;
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public Button Commande(string nom) => boutons.TryGetValue(nom, out var b) ? b : null;
        public string TexteDe(string nom) => textes.TryGetValue(nom, out var t) ? t.text : "";

        Func<string> maison; Func<CelluleDeCarte> retenue; NomsDesTerres noms; int port;
        Text etat, message; readonly Dictionary<string, Button> boutons = new Dictionary<string, Button>(); readonly Dictionary<string, Text> textes = new Dictionary<string, Text>();
        Text legendeHommes, legendeVivres;
        Task<(Lecture<OrdresDeGuerre> ordres, Lecture<GuerresLues> guerres, Dictionary<string, string> noms)> vol; double prochaine; long? celluleLue; string maisonLue;
        readonly Dictionary<string, string> nomsDesMaisons = new Dictionary<string, string>();
        long? armeeChoisie; string preparePour, nomPrepare; RecuIntention recuVu; EtatLecture? etatDuRecu; string texteDuRecu;

        public void Initialiser(Transform toile, Transform dossier, Func<string> maison, Func<CelluleDeCarte> retenue, OrdreConfirme ordre, NomsDesTerres noms, int port)
        {
            this.maison = maison ?? throw new ArgumentNullException(nameof(maison)); this.retenue = retenue ?? (() => null);
            Ordre = ordre ?? throw new ArgumentNullException(nameof(ordre)); this.noms = noms; this.port = port;
            Feuillet = gameObject.AddComponent<Feuillet>(); Feuillet.Initialiser(toile, TITRE);
            // Dans l'en-tête du panneau « Votre maison », entre son titre et sa croix : la barre du haut n'a plus de place entre ses dossiers et le temps.
            var ouvrir = SocleInterface.Commande(dossier, COMMANDE, 340, 20, () => { if (Feuillet.Ouvert) Feuillet.Fermer(); else { Feuillet.Ouvrir(); prochaine = 0; } },
                phrase: "La guerre : ouvre ou ferme vos guerres, vos armées et les ordres de guerre, avec leur prix.");
            Taille(ouvrir, 160);
            // Chaque texte garde sous lui la place de son écriture la plus longue (son refus compris) : aucun ne passe sous
            // le curseur ou le bouton qui le suit. Le panneau descend donc plus bas que le feuillet des guerres.
            Panneau = SocleInterface.Panneau(Feuillet.Cadre, ORDRES, 764, 0, 500, 892);
            etat = Texte("État des ordres", "Lecture des ordres…", 88, 28, SocleInterface.Corps);
            Texte(LEVER, "", 120, 112, 16);
            CurseurHommes = Curseur("Hommes à lever", 236, n => legendeHommes.text = Hommes((long)n)); legendeHommes = Legende("Hommes levés", 236);
            CurseurVivres = Curseur("Vivres emportés", 266, n => legendeVivres.text = TexteDuMonde.Masse(n) + " de vivres"); legendeVivres = Legende("Vivres levés", 266);
            Bouton(LEVER, 24, 296, LARGEUR, Lever, "Lever l'ost : prépare la levée des hommes et des vivres choisis, sans l'envoyer ; « " + CONFIRMER + " » l'envoie.");
            Texte(DECLARER, "", 350, 92, 16);
            Bouton(DECLARER, 24, 444, LARGEUR, Declarer, "Déclarer la guerre : prépare la déclaration au maître de la terre gardée sur la carte, sans l'envoyer.");
            Texte("Armée choisie", "", 498, 52, 16).rectTransform.sizeDelta = new Vector2(296, 52);
            Bouton(SUIVANTE, 328, 498, 148, () => Suivante(), "Armée suivante : montre les ordres d'une autre de vos armées.");
            Texte("Ordres de l'armée", "", 556, 136, 16);
            Bouton(MARCHER, 24, 696, 144, () => OrdreDArmee(MARCHER), "Marcher : prépare la marche de l'armée vers le bourg de la terre gardée sur la carte, sans l'envoyer.");
            Bouton(ASSIEGER, 176, 696, 144, () => OrdreDArmee(ASSIEGER), "Assiéger : prépare le siège de la place où se tient l'armée, sans l'envoyer.");
            Bouton(RENVOYER, 328, 696, 148, () => OrdreDArmee(RENVOYER), "Renvoyer : prépare le retour des hommes dans leurs lieux et des vivres au grenier, sans l'envoyer.");
            message = Texte("Message des ordres", "", 748, 72, 16);
            Bouton(RETOUR, 24, 824, 200, () => { Ordre.Recommencer(); preparePour = null; nomPrepare = null; }, "Abandonne l'ordre préparé, ou referme son reçu ; rien n'est envoyé.");
            Bouton(CONFIRMER, 236, 824, 240, () => { if (!Ordre.EnCours && Ordre.Brouillon != null && Ordre.Recu == null && preparePour == maison()) _ = Ordre.Confirmer(); },
                "Envoie l'ordre de guerre préparé au monde ; il l'applique au jour suivant.");
            MatieresCabinet.Engagement(boutons[CONFIRMER]);
            foreach (var t in Feuillet.Cadre.GetComponentsInChildren<Text>(true)) t.supportRichText = false;
            LecteurOrdres = (m, c) => { using (var client = new ClientGuerre(this.port, DELAI)) return client.LireOrdres(m, c); };
            LecteurGuerres = () => { using (var client = new ClientGuerre(this.port, DELAI)) return client.LireGuerres(); };
            LecteurMaison = id => { using (var client = new ClientMaison(this.port, DELAI)) return client.Lire(id); };
            Afficher(0);
        }

        static void Taille(Button b, float largeur)
        {
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
            b.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, SocleInterface.HauteurCommande);
        }
        void Bouton(string nom, float x, float y, float largeur, Action action, string phrase) { var b = SocleInterface.Commande(Panneau, nom, x, y, action, phrase: phrase); Taille(b, largeur); boutons[nom] = b; }
        Text Texte(string nom, string contenu, float y, float hauteur, int taille)
        {
            var t = SocleInterface.Texte(Panneau, contenu, 24, y, LARGEUR, taille); t.name = nom; t.rectTransform.sizeDelta = new Vector2(LARGEUR, hauteur);
            t.verticalOverflow = VerticalWrapMode.Overflow; t.horizontalOverflow = HorizontalWrapMode.Wrap; textes[nom] = t; return t;
        }
        Text Legende(string nom, float y) { var t = SocleInterface.Texte(Panneau, "", 316, y, 160, 16); t.name = nom; t.rectTransform.sizeDelta = new Vector2(160, 24); t.alignment = TextAnchor.MiddleLeft; return t; }
        Slider Curseur(string nom, float y, Action<float> regler)
        {
            var piste = new GameObject(nom, typeof(RectTransform), typeof(Image), typeof(Slider)); var rect = piste.GetComponent<RectTransform>(); rect.SetParent(Panneau, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1); rect.anchoredPosition = new Vector2(24, -y); rect.sizeDelta = new Vector2(280, 24);
            piste.GetComponent<Image>().color = SocleInterface.Couleur("secondaire");
            var niveau = new GameObject("Niveau", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>(); niveau.SetParent(rect, false);
            niveau.anchorMin = Vector2.zero; niveau.anchorMax = Vector2.one; niveau.offsetMin = niveau.offsetMax = Vector2.zero;
            var remplissage = niveau.GetComponent<Image>(); remplissage.color = SocleInterface.Couleur("accent"); remplissage.raycastTarget = false;
            var poignee = new GameObject("Poignée", typeof(RectTransform), typeof(Image)).GetComponent<RectTransform>(); poignee.SetParent(rect, false); poignee.sizeDelta = new Vector2(20, 0);
            var image = poignee.GetComponent<Image>(); image.color = SocleInterface.Couleur("papier");
            var slider = piste.GetComponent<Slider>(); slider.fillRect = niveau; slider.handleRect = poignee; slider.targetGraphic = image;
            slider.direction = Slider.Direction.LeftToRight; slider.minValue = 0; slider.maxValue = 0; slider.wholeNumbers = true; slider.onValueChanged.AddListener(v => regler(v));
            return slider;
        }

        void LateUpdate() => Pas(Time.realtimeSinceStartupAsDouble);

        public void Pas(double maintenant)
        {
            if (Feuillet == null) return;
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; Appliquer(fini); }
            string id = maison(); long? cell = retenue()?.CellId;
            if (Feuillet.Ouvert && id != null && vol == null && (maintenant >= prochaine || cell != celluleLue || id != maisonLue))
            {
                prochaine = maintenant + PERIODE_S; celluleLue = cell; maisonLue = id;
                var lireOrdres = LecteurOrdres; var lireGuerres = LecteurGuerres; var lireMaison = LecteurMaison; var connus = new HashSet<string>(nomsDesMaisons.Keys);
                vol = Task.Run(() =>
                {
                    var ordres = SansFaute(() => lireOrdres(id, cell), "ordres"); var guerres = SansFaute(lireGuerres, "guerres");
                    var voulus = new HashSet<string>();
                    if (ordres.Presente && ordres.Donnees.Cible?.Maitre != null) voulus.Add(ordres.Donnees.Cible.Maitre);
                    if (guerres.Presente) foreach (var g in guerres.Donnees.Guerres) { voulus.Add(g.Agresseur); voulus.Add(g.Defenseur); }
                    if (guerres.Presente) foreach (var p in guerres.Donnees.Prises) { if (p.De != null) voulus.Add(p.De); voulus.Add(p.A); }
                    var lus = new Dictionary<string, string>();
                    foreach (var m in voulus.Where(m => m != id && !connus.Contains(m)))
                    {
                        var lue = SansFaute(() => lireMaison(m), "maison");
                        if (lue.Presente && lue.Donnees.Nom != null) lus[m] = lue.Donnees.Nom;
                    }
                    return (ordres, guerres, lus);
                });
            }
            Afficher(maintenant);
        }

        static Lecture<T> SansFaute<T>(Func<Lecture<T>> lire, string quoi) where T : class
        {
            try { return lire() ?? Lecture<T>.Absent(quoi + " : aucune lecture rendue"); }
            catch (Exception e) { return Lecture<T>.Absent(quoi + " : " + e.GetBaseException().Message); }
        }

        void Appliquer(Task<(Lecture<OrdresDeGuerre> ordres, Lecture<GuerresLues> guerres, Dictionary<string, string> noms)> fini)
        {
            if (fini.IsFaulted) { string cause = fini.Exception.GetBaseException().Message; Ordres = Lecture<OrdresDeGuerre>.Absent("ordres : " + cause); Guerres = Lecture<GuerresLues>.Absent("guerres : " + cause); return; }
            Ordres = fini.Result.ordres; Guerres = fini.Result.guerres;
            foreach (var paire in fini.Result.noms) nomsDesMaisons[paire.Key] = paire.Value;
            if (Ordres.Presente)
            {
                var levee = Ordres.Donnees.Levee; float hommes = CurseurHommes.value, vivres = CurseurVivres.value;
                CurseurHommes.maxValue = IntentionsDeGuerre.Maximum(levee); CurseurVivres.maxValue = (float)Math.Floor(levee.GrainLibreKg);
                CurseurHommes.SetValueWithoutNotify(Mathf.Min(hommes, CurseurHommes.maxValue)); CurseurVivres.SetValueWithoutNotify(Mathf.Min(vivres, CurseurVivres.maxValue));
                legendeHommes.text = Hommes((long)CurseurHommes.value); legendeVivres.text = TexteDuMonde.Masse(CurseurVivres.value) + " de vivres";
            }
        }

        // Les états, dans l'ordre de `GestesDesJauges` : 1 à 5 attendent ou se taisent, 6 montre les ordres.
        int Code(out string texte)
        {
            string id = maison();
            if (id == null) { texte = "Choisissez une maison pour faire la guerre."; return 3; }
            if (Ordres == null) { texte = "Lecture des ordres…"; return 1; }
            if (!Ordres.Presente) { texte = "Ordres indisponibles : " + TexteDuMonde.Absence(Ordres.Absence, id); return 5; }
            if (Ordres.Donnees.MaisonId != id || maisonLue != id || (Ordres.Donnees.Cible?.CellId ?? (long?)null) != retenue()?.CellId) { texte = "Ordres en attente du monde"; return 4; }
            texte = "Ordres de votre maison · relevé au " + TexteDuMonde.Date(Ordres.Donnees.Date); return 6;
        }

        OrdresDUneArmee Armee()
        {
            if (Ordres == null || !Ordres.Presente || Ordres.Donnees.Armees.Count == 0) return null;
            return Ordres.Donnees.Armees.FirstOrDefault(a => a.Identifiant == armeeChoisie) ?? Ordres.Donnees.Armees[0];
        }
        void Suivante()
        {
            var armees = Ordres?.Presente == true ? Ordres.Donnees.Armees : null; if (armees == null || armees.Count < 2) return;
            int i = armees.ToList().FindIndex(a => a.Identifiant == Armee().Identifiant); armeeChoisie = armees[(i + 1) % armees.Count].Identifiant;
        }

        public void Afficher(double maintenant)
        {
            int code = Code(out string texte); etat.text = texte; string id = maison();
            bool libre = Ordre.Brouillon == null && Ordre.Recu == null && !Ordre.EnCours, pret = code == 6 && libre;
            var ordres = code == 6 ? Ordres.Donnees : null; var armee = code == 6 ? Armee() : null;
            // La levée.
            var levee = ordres?.Levee; long maximum = levee == null ? 0 : IntentionsDeGuerre.Maximum(levee);
            textes[LEVER].text = levee == null ? LEVER + " : en attente du devis du monde."
                : LEVER + " : jusqu'à " + Hommes(maximum) + " de votre capitale, pris aux champs ; vivres jusqu'à " + TexteDuMonde.Masse(levee.GrainLibreKg)
                  + " du grenier, ration de " + TexteDuMonde.Masse(levee.RationKgParHommeParJour) + " par homme et par jour." + Refus(levee.Refus, id);
            CurseurHommes.interactable = CurseurVivres.interactable = pret && levee?.Refus == null && maximum > 0;
            boutons[LEVER].interactable = pret && levee != null && levee.Refus == null && CurseurHommes.value > 0;
            // La déclaration, au maître de la terre gardée.
            var cible = ordres?.Cible;
            textes[DECLARER].text = ordres == null ? DECLARER + " : en attente du devis du monde."
                : cible == null ? DECLARER + " : gardez une terre sur la carte pour viser son maître."
                : cible.Maitre == null ? DECLARER + " : personne ne tient le bourg de la terre gardée." + Refus(cible.RefusDeDeclaration, id)
                : DECLARER + " à " + NomDeMaison(cible.Maitre) + " : la déclaration ne coûte rien ; elle ouvre le siège de ses places." + Refus(cible.RefusDeDeclaration, id);
            boutons[DECLARER].interactable = pret && cible?.Maitre != null && cible.RefusDeDeclaration == null;
            // L'armée choisie et ses trois ordres.
            textes["Armée choisie"].text = ordres == null ? "Armées en attente du devis du monde." : armee == null ? "Aucune armée : levez l'ost pour en former une."
                : "Armée choisie : " + Hommes(armee.Hommes) + " à " + NomDuLieu(armee.CellId, armee.Rang, maintenant) + " · " + Situation(armee.Siege, armee.Destination, maintenant) + " · vivres " + TexteDuMonde.Masse(armee.VivresKg);
            boutons[SUIVANTE].interactable = ordres != null && ordres.Armees.Count > 1;
            textes["Ordres de l'armée"].text = armee == null ? "" : string.Join("\n",
                armee.Marche == null ? MARCHER + " : gardez une terre sur la carte pour viser son bourg."
                    : MARCHER + " vers " + NomDuLieu(cible.CellId, 0, maintenant) + (armee.Marche.Refus == null ? " : " + TexteDuMonde.Jours(armee.Marche.Jours) + ", " + TexteDuMonde.Nombre((long)Math.Round(armee.Marche.Km)) + " km" : "") + EnLigne(armee.Marche.Refus, id),
                ASSIEGER + " la place où se tient l'armée" + EnLigne(armee.RefusDuSiege, id),
                RENVOYER + " : " + Hommes(armee.HommesRendus) + " rentrent aux champs, " + TexteDuMonde.Masse(armee.VivresRendusKg) + " de vivres au grenier" + EnLigne(armee.RefusDuRenvoi, id));
            boutons[MARCHER].interactable = pret && armee?.Marche != null && armee.Marche.Refus == null;
            boutons[ASSIEGER].interactable = pret && armee != null && armee.RefusDuSiege == null;
            boutons[RENVOYER].interactable = pret && armee != null && armee.RefusDuRenvoi == null;
            // Le brouillon, le reçu, et le feuillet de gauche.
            bool brouillon = Ordre.Brouillon != null, recu = Ordre.Recu != null;
            boutons[CONFIRMER].gameObject.SetActive(brouillon && !recu); boutons[CONFIRMER].interactable = !Ordre.EnCours && code == 6 && preparePour == id;
            boutons[RETOUR].gameObject.SetActive(brouillon || recu); boutons[RETOUR].interactable = !Ordre.EnCours;
            Message(id);
            if (Feuillet.Ouvert) { TexteAffiche = Recit(id, maintenant); Feuillet.Ecrire(TexteAffiche); }
        }

        void Message(string id)
        {
            if (Ordre.EnCours) { Normal("Envoi en cours. Attendez le reçu."); return; }
            if (!ReferenceEquals(Ordre.Recu, recuVu)) { recuVu = Ordre.Recu; Noter(recuVu, id); }
            if (Ordre.Recu != null) { if (etatDuRecu == null) Normal(texteDuRecu); else EtatsLecture.Afficher(message, etatDuRecu.Value, texteDuRecu); }
            else if (Ordre.Brouillon != null) Normal(Ordre.Resume);
            else Normal("Choisissez un ordre : son prix se lit avant l'envoi.");
            message.rectTransform.sizeDelta = new Vector2(LARGEUR, 72);
        }
        void Normal(string texte) { message.text = texte; message.color = SocleInterface.Couleur("encre"); }
        void Noter(RecuIntention recu, string id)
        {
            etatDuRecu = null; texteDuRecu = null; if (recu == null) return;
            string nom = nomPrepare ?? "Ordre";
            if (recu.Acceptee) { texteDuRecu = nom + " : ordre reçu. Le monde l'applique au jour suivant."; prochaine = 0; }
            else if (recu.Presente) { etatDuRecu = EtatLecture.Refus; texteDuRecu = nom + " : " + GestesDesJauges.Raison(recu.Erreur, id); }
            else { etatDuRecu = EtatLecture.Panne; texteDuRecu = "Envoi non confirmé : " + TexteDuMonde.Absence(recu.Absence) + ". Vérifiez le monde avant tout nouvel ordre."; }
        }

        void Preparer(string nom, string json, string resume)
        {
            string id = maison();
            if (Code(out _) != 6 || Ordre.Brouillon != null || Ordre.Recu != null || Ordre.EnCours) return;
            if (Ordre.Preparer(json, resume + " Confirmez pour envoyer l'ordre.")) { preparePour = id; nomPrepare = nom; }
        }
        void Lever()
        {
            if (!boutons[LEVER].interactable) return;
            var levee = Ordres.Donnees.Levee; long hommes = (long)CurseurHommes.value, vivres = (long)CurseurVivres.value;
            Preparer(LEVER, IntentionsDeGuerre.Lever(maison(), IntentionsDeGuerre.Repartir(levee, hommes), vivres), LEVER + " : " + Hommes(hommes) + " et " + TexteDuMonde.Masse(vivres) + " de vivres.");
        }
        void Declarer()
        {
            if (!boutons[DECLARER].interactable) return;
            var cible = Ordres.Donnees.Cible; Preparer(DECLARER, IntentionsDeGuerre.Declarer(maison(), cible.Maitre), DECLARER + " à " + NomDeMaison(cible.Maitre) + ".");
        }
        void OrdreDArmee(string nom)
        {
            if (!boutons[nom].interactable) return;
            var armee = Armee(); string id = maison();
            if (nom == MARCHER) Preparer(nom, IntentionsDeGuerre.Marcher(id, armee.Identifiant, Ordres.Donnees.Cible.CellId), textes["Ordres de l'armée"].text.Split('\n')[0] + ".");
            else if (nom == ASSIEGER) Preparer(nom, IntentionsDeGuerre.Assieger(id, armee.Identifiant), ASSIEGER + " la place où se tient l'armée.");
            else Preparer(nom, IntentionsDeGuerre.Renvoyer(id, armee.Identifiant), RENVOYER + " l'armée : " + Hommes(armee.HommesRendus) + " rentrent aux champs.");
        }

        // Mes guerres, contre qui et depuis combien de jours servis ; mes armées ; les terres prises et perdues.
        string Recit(string id, double maintenant)
        {
            if (id == null) return "Choisissez une maison pour faire la guerre.";
            if (Guerres == null) return "Lecture des guerres…";
            if (!Guerres.Presente) return "Guerres indisponibles : " + TexteDuMonde.Absence(Guerres.Absence, id);
            var lues = Guerres.Donnees; var sb = new StringBuilder("VOS GUERRES");
            var miennes = lues.Guerres.Where(g => g.Agresseur == id || g.Defenseur == id).ToList();
            if (miennes.Count == 0) sb.Append("\nAucune guerre.");
            foreach (var g in miennes)
                sb.Append('\n').Append("Contre ").Append(NomDeMaison(g.Agresseur == id ? g.Defenseur : g.Agresseur))
                  .Append(g.Agresseur == id ? ", déclarée par vous" : ", déclarée contre vous").Append(", depuis ").Append(TexteDuMonde.Jours(Math.Max(0, lues.Tick - g.Debut)));
            sb.Append("\n\nVOS ARMÉES");
            var armees = lues.Armees.Where(a => a.Maison == id).ToList();
            if (armees.Count == 0) sb.Append("\nAucune armée.");
            foreach (var a in armees)
                sb.Append('\n').Append(Hommes(a.Hommes)).Append(" à ").Append(NomDuLieu(a.CellId, a.Rang, maintenant)).Append(" · ").Append(Situation(a.Siege, a.Destination, maintenant))
                  .Append(" · vivres ").Append(TexteDuMonde.Masse(a.VivresKg));
            var prises = lues.Prises.Where(p => p.A == id || p.De == id).ToList();
            if (prises.Count > 0) sb.Append("\n\nTERRES PRISES ET PERDUES");
            foreach (var p in prises)
                sb.Append('\n').Append(NomDuLieu(p.CellId, 0, maintenant)).Append(p.A == id ? " prise à " + (p.De == null ? "une terre sans maître" : NomDeMaison(p.De)) : " perdue au profit de " + NomDeMaison(p.A));
            sb.Append("\n\nRelevé au ").Append(TexteDuMonde.Date(lues.Date)).Append('.');
            return sb.ToString();
        }

        string Situation(long? siege, LieuDuPays destination, double maintenant) =>
            siege != null ? "au siège de " + NomDuLieu(siege.Value, 0, maintenant) : destination != null ? "en marche vers " + NomDuLieu(destination.CellId, destination.Rang, maintenant) : "à l'arrêt";
        string NomDuLieu(long cell, long rang, double maintenant) => noms?.Nom(cell, rang, maintenant) ?? "un lieu sans nom lu";
        string NomDeMaison(string id) => id != null && nomsDesMaisons.TryGetValue(id, out var nom) ? nom : "une maison sans nom lu";
        static string Hommes(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " hommes" : " homme");
        static string Refus(string raison, string maison) => raison == null ? "" : "\nRefusé d'avance : " + GestesDesJauges.Raison(raison, maison);
        // Sur la ligne de son ordre : les trois ordres d'une armée tiennent chacun sur sa ligne.
        static string EnLigne(string raison, string maison) => raison == null ? "" : " — refusé d'avance : " + GestesDesJauges.Raison(raison, maison);
    }
}
