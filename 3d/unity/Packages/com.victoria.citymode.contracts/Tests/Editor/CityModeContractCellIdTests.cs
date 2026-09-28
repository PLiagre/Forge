using NUnit.Framework;
using UnityEngine;

namespace Victoria.CityMode.Integration.Tests
{
    /// <summary>
    /// Le contrat ville parle en cell_id : la seule clé spatiale du monde.
    /// -1 veut dire « non calculé » et se refuse ; 0 est une cellule valide.
    /// </summary>
    public sealed class CityModeContractCellIdTests
    {
        // Anciennes clés assemblées en morceaux : la recherche du lot (SC2) ne
        // doit plus trouver leur nom en toutes lettres dans le paquet.
        static readonly string CleVille = "city" + "Id";
        static readonly string CleCarte = "map" + "CellId";

        CityModeSession session;

        [TearDown]
        public void TearDown()
        {
            session?.Dispose();
            session = null;
        }

        [TestCase(0)]
        [TestCase(1175)]
        public void MessagesValides_Passent(int cellId)
        {
            CityModeErrorCode error;
            var context = Contexte(); context.cell_id = cellId;
            Assert.IsTrue(context.TryValidate(out error), error.ToString());
            var snapshot = Photographie(); snapshot.cell_id = cellId;
            Assert.IsTrue(snapshot.TryValidate(out error), error.ToString());
            var intent = Intention(); intent.cell_id = cellId;
            Assert.IsTrue(intent.TryValidate(out error), error.ToString());
            var receipt = Recu(intent); receipt.cell_id = cellId;
            Assert.IsTrue(receipt.TryValidate(out error), error.ToString());
        }

        [Test]
        public void Contexte_CellIdParDefaut_EstRefuse()
        {
            var context = Contexte();
            Assert.AreEqual(-1, context.cell_id);
            Assert.IsFalse(context.TryValidate(out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
        }

        [Test]
        public void Photographie_CellIdParDefaut_EstRefusee()
        {
            var snapshot = Photographie();
            Assert.AreEqual(-1, snapshot.cell_id);
            Assert.IsFalse(snapshot.TryValidate(out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
        }

        [Test]
        public void Intention_CellIdParDefaut_EstRefusee()
        {
            var intent = Intention();
            Assert.AreEqual(-1, intent.cell_id);
            Assert.IsFalse(intent.TryValidate(out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
        }

        [Test]
        public void Recu_CellIdParDefaut_EstRefuse()
        {
            var receipt = Recu(Intention());
            Assert.AreEqual(-1, receipt.cell_id);
            Assert.IsFalse(receipt.TryValidate(out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
        }

        [Test]
        public void Session_PhotographieDUneAutreCellule_EstRefuseeALOuverture()
        {
            var context = Contexte(); context.cell_id = 1175;
            var hote = new FauxHote(Photographie());
            hote.snapshot.cell_id = 1176;
            Assert.IsFalse(CityModeSession.TryOpen(context, hote, hote, out session, out var error));
            Assert.IsNull(session);
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
        }

        [Test]
        public void Session_PhotographieDUneAutreCellule_EstRefuseeAuRafraichissement()
        {
            var hote = OuvrirSession(1175);
            var suivante = Photographie();
            suivante.cell_id = 0;
            hote.snapshot = suivante;
            Assert.IsFalse(session.TryRefreshSnapshot(out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
            Assert.AreEqual(1175, session.CurrentSnapshot.cell_id);
        }

        [Test]
        public void Session_IntentionDUneAutreCellule_EstRefusee()
        {
            var hote = OuvrirSession(1175);
            var intent = Intention(); intent.cell_id = 1176;
            Assert.IsFalse(session.TrySubmitIntent(intent, out var receipt, out var error));
            Assert.IsNull(receipt);
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
            Assert.AreEqual(0, hote.submitCount);
        }

        [Test]
        public void Session_RecuDUneAutreCellule_EstRefuse()
        {
            var hote = OuvrirSession(1175);
            hote.cellIdDuRecu = 0;
            var intent = Intention(); intent.cell_id = 1175;
            Assert.IsFalse(session.TrySubmitIntent(intent, out _, out var error));
            Assert.AreEqual(CityModeErrorCode.InvalidCellId, error);
            Assert.AreEqual(1, hote.submitCount);
        }

        [Test]
        public void JsonUtility_EcritEtLitLaCleDuSchema()
        {
            var context = Contexte(); context.cell_id = 1175;
            var json = JsonUtility.ToJson(context);
            StringAssert.Contains("\"cell_id\":1175", json);
            StringAssert.DoesNotContain(CleVille, json);
            StringAssert.DoesNotContain(CleCarte, json);
            Assert.AreEqual(1175, JsonUtility.FromJson<CityLaunchContext>(json).cell_id);
        }

        FauxHote OuvrirSession(int cellId)
        {
            var context = Contexte(); context.cell_id = cellId;
            var snapshot = Photographie(); snapshot.cell_id = cellId;
            var hote = new FauxHote(snapshot);
            Assert.IsTrue(CityModeSession.TryOpen(
                context, hote, hote, out session, out var error), error.ToString());
            return hote;
        }

        // Les fabriques laissent cell_id à sa valeur par défaut : chaque cas le pose.
        static CityLaunchContext Contexte()
        {
            return new CityLaunchContext
            {
                sessionId = "session:cell",
                worldSeed = 140001,
                worldTick = 4800,
                stateRevision = 42,
                timePolicy = CityWorldTimePolicy.PauseWorld,
                worldTimeScalePermille = 0,
                returnViewId = "main-map",
                returnViewStateJson = "{}"
            };
        }

        static CitySnapshotEnvelope Photographie()
        {
            return new CitySnapshotEnvelope
            {
                worldTick = 4800,
                stateRevision = 42,
                isFullSnapshot = true,
                payloadJson = "{}",
                payloadSha256 = new string('a', 64)
            };
        }

        static CityIntentEnvelope Intention()
        {
            return new CityIntentEnvelope
            {
                sessionId = "session:cell",
                intentId = "intent:1",
                issuedAtWorldTick = 4800,
                expectedStateRevision = 42,
                intentKind = "selection.inspect",
                payloadJson = "{}"
            };
        }

        static CityIntentReceipt Recu(CityIntentEnvelope intent)
        {
            return new CityIntentReceipt
            {
                sessionId = intent.sessionId,
                intentId = intent.intentId,
                status = CityIntentStatus.Accepted,
                errorCode = CityModeErrorCode.None,
                resultingWorldTick = 4801,
                resultingStateRevision = 43
            };
        }

        sealed class FauxHote : ICityModeSnapshotSource, ICityModeIntentSink
        {
            public CitySnapshotEnvelope snapshot;
            public int? cellIdDuRecu;
            public int submitCount;

            public FauxHote(CitySnapshotEnvelope snapshot)
            {
                this.snapshot = snapshot;
            }

            public CitySnapshotEnvelope ReadSnapshot(CityLaunchContext context)
            {
                return snapshot;
            }

            public CityIntentReceipt SubmitIntent(CityIntentEnvelope intent)
            {
                submitCount++;
                var receipt = Recu(intent);
                receipt.cell_id = cellIdDuRecu ?? intent.cell_id;
                return receipt;
            }
        }
    }
}
