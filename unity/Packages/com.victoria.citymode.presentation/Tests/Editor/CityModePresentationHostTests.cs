using System.Linq;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Presentation.Tests
{
    public sealed class CityModePresentationHostTests
    {
        CityModeSession session;
        CityModePresentationHost presentation;

        [TearDown]
        public void TearDown()
        {
            presentation?.Dispose();
            presentation = null;
            session?.Dispose();
            session = null;
            foreach (var orphan in Object.FindObjectsByType<CityModePresentationHost>(
                FindObjectsInactive.Include, FindObjectsSortMode.None))
                Object.DestroyImmediate(orphan.gameObject);
        }

        [Test]
        public void Package_HasNoAutomaticRuntimeBootstrap()
        {
            var methods = typeof(CityModePresentationHost).GetMethods(
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static |
                BindingFlags.Instance);
            Assert.IsFalse(methods.Any(method => method
                .GetCustomAttributes(typeof(RuntimeInitializeOnLoadMethodAttribute), false)
                .Any()));
            Assert.IsFalse(CityModePresentationHost.HasActiveInstance);
        }

        [Test]
        public void Host_ExplicitlyCreatesOnePresentationAndDestroysItIdempotently()
        {
            OpenSession(out var error);
            Assert.IsTrue(CityModePresentationHost.TryCreate(
                session, out presentation, out error), error.ToString());
            Assert.IsTrue(presentation.IsBound);
            Assert.IsTrue(CityModePresentationHost.HasActiveInstance);

            Assert.IsFalse(CityModePresentationHost.TryCreate(
                session, out var duplicate, out error));
            Assert.IsNull(duplicate);
            Assert.AreEqual(CityModeErrorCode.SessionAlreadyActive, error);

            presentation.Dispose();
            presentation.Dispose();
            presentation = null;
            Assert.IsFalse(CityModePresentationHost.HasActiveInstance);
            Assert.IsTrue(CityModePresentationHost.TryCreate(
                session, out presentation, out error), error.ToString());
        }

        [Test]
        public void ViewReceivesAuthoritativeSnapshotReceiptAndRefresh()
        {
            var gateway = OpenSession(out var error);
            Assert.IsTrue(CityModePresentationHost.TryCreate(
                session, out presentation, out error), error.ToString());
            var view = new RecordingView();
            Assert.IsTrue(presentation.TryAttachView(view, out error), error.ToString());
            Assert.AreEqual("city:minimal", view.openedCityId);
            Assert.AreEqual(7, view.presentedRevision);

            var intent = new CityIntentEnvelope
            {
                sessionId = "session:minimal",
                intentId = "intent:1",
                cityId = "city:minimal",
                issuedAtWorldTick = 20,
                expectedStateRevision = 7,
                intentKind = "selection.inspect",
                payloadJson = "{}"
            };
            Assert.IsTrue(presentation.TrySubmitIntent(
                intent, out var receipt, out error), error.ToString());
            Assert.AreEqual(CityIntentStatus.Accepted, receipt.status);
            Assert.AreEqual("intent:1", view.completedIntentId);
            Assert.IsTrue(presentation.TryRefreshSnapshot(out error), error.ToString());
            Assert.AreEqual(8, view.presentedRevision);
            Assert.AreEqual(1, gateway.submitCount);

            presentation.Dispose();
            presentation = null;
            Assert.AreEqual(1, view.closeCount);
        }

        FakeGateway OpenSession(out CityModeErrorCode error)
        {
            var context = new CityLaunchContext
            {
                sessionId = "session:minimal",
                cityId = "city:minimal",
                mapCellId = "cell:minimal",
                worldSeed = 31,
                worldTick = 20,
                stateRevision = 7,
                timePolicy = CityWorldTimePolicy.PauseWorld,
                worldTimeScalePermille = 0,
                returnViewId = "map",
                returnViewStateJson = "{}"
            };
            var gateway = new FakeGateway(context);
            Assert.IsTrue(CityModeSession.TryOpen(
                context, gateway, gateway, out session, out error), error.ToString());
            return gateway;
        }

        sealed class RecordingView : ICityModePresentationView
        {
            public string openedCityId;
            public long presentedRevision = -1;
            public string completedIntentId;
            public int closeCount;

            public void Open(CityLaunchContext context)
            {
                openedCityId = context.cityId;
            }

            public void Present(CitySnapshotEnvelope snapshot)
            {
                presentedRevision = snapshot.stateRevision;
            }

            public void CompleteIntent(CityIntentReceipt receipt)
            {
                completedIntentId = receipt.intentId;
            }

            public void Close()
            {
                closeCount++;
            }
        }

        sealed class FakeGateway : ICityModeSnapshotSource, ICityModeIntentSink
        {
            CitySnapshotEnvelope snapshot;
            public int submitCount;

            public FakeGateway(CityLaunchContext context)
            {
                snapshot = new CitySnapshotEnvelope
                {
                    cityId = context.cityId,
                    worldTick = context.worldTick,
                    stateRevision = context.stateRevision,
                    isFullSnapshot = true,
                    payloadJson = "{}",
                    payloadSha256 = new string('a', 64)
                };
            }

            public CitySnapshotEnvelope ReadSnapshot(CityLaunchContext context)
            {
                return snapshot;
            }

            public CityIntentReceipt SubmitIntent(CityIntentEnvelope intent)
            {
                submitCount++;
                snapshot = new CitySnapshotEnvelope
                {
                    cityId = snapshot.cityId,
                    worldTick = snapshot.worldTick + 1,
                    stateRevision = snapshot.stateRevision + 1,
                    isFullSnapshot = true,
                    payloadJson = "{\"accepted\":true}",
                    payloadSha256 = new string('b', 64)
                };
                return new CityIntentReceipt
                {
                    sessionId = intent.sessionId,
                    intentId = intent.intentId,
                    cityId = intent.cityId,
                    status = CityIntentStatus.Accepted,
                    errorCode = CityModeErrorCode.None,
                    resultingWorldTick = snapshot.worldTick,
                    resultingStateRevision = snapshot.stateRevision
                };
            }
        }
    }
}
