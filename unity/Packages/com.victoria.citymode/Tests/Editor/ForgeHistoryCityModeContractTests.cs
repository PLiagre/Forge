using NUnit.Framework;
using Victoria.CityMode.Integration;

namespace Victoria.CityMode.Tests
{
    public sealed class ForgeHistoryCityModeContractTests
    {
        [Test]
        public void LaunchContext_RequiresOpaqueHostIdentityAndReturnView()
        {
            var context = ValidContext();
            Assert.IsTrue(context.TryValidate(out var error), error.ToString());

            context.cityId = string.Empty;
            Assert.IsFalse(context.TryValidate(out error));
            Assert.AreEqual(CityModeErrorCode.InvalidCityId, error);
        }

        [TestCase(CityWorldTimePolicy.PauseWorld, 0, true)]
        [TestCase(CityWorldTimePolicy.PauseWorld, 1000, false)]
        [TestCase(CityWorldTimePolicy.ContinueWorld, 1000, true)]
        [TestCase(CityWorldTimePolicy.ContinueWorld, 0, false)]
        [TestCase(CityWorldTimePolicy.ScaledWorld, 250, true)]
        [TestCase(CityWorldTimePolicy.ScaledWorld, 0, false)]
        public void LaunchContext_TimePolicyIsExplicit(
            CityWorldTimePolicy policy, int scalePermille, bool expected)
        {
            var context = ValidContext();
            context.timePolicy = policy;
            context.worldTimeScalePermille = scalePermille;
            Assert.AreEqual(expected, context.TryValidate(out _));
        }

        [Test]
        public void Snapshot_RequiresFullVersionedHashedPayload()
        {
            var snapshot = new CitySnapshotEnvelope
            {
                cityId = "city:1001",
                worldTick = 4800,
                stateRevision = 42,
                isFullSnapshot = true,
                payloadJson = "{\"population\":30}",
                payloadSha256 = new string('a', 64)
            };
            Assert.IsTrue(snapshot.TryValidate(out var error), error.ToString());

            snapshot.payloadSha256 = "not-a-sha";
            Assert.IsFalse(snapshot.TryValidate(out error));
            Assert.AreEqual(CityModeErrorCode.InvalidPayload, error);
        }

        [Test]
        public void Intent_CarriesCorrelationAndExpectedRevision()
        {
            var intent = ValidIntent();
            Assert.IsTrue(intent.TryValidate(out var error), error.ToString());

            intent.expectedStateRevision = -1;
            Assert.IsFalse(intent.TryValidate(out error));
            Assert.AreEqual(CityModeErrorCode.InvalidStateRevision, error);
        }

        [Test]
        public void Receipt_RequiresStatusErrorConsistency()
        {
            var receipt = new CityIntentReceipt
            {
                sessionId = "session:test",
                intentId = "intent:0001",
                cityId = "city:1001",
                status = CityIntentStatus.Accepted,
                errorCode = CityModeErrorCode.None,
                resultingWorldTick = 4801,
                resultingStateRevision = 43
            };
            Assert.IsTrue(receipt.TryValidate(out var error), error.ToString());

            receipt.errorCode = CityModeErrorCode.RevisionConflict;
            Assert.IsFalse(receipt.TryValidate(out error));
            Assert.AreEqual(CityModeErrorCode.InvalidPayload, error);
        }

        [Test]
        public void RevisionConflict_IsAnExplicitRecoverableReceipt()
        {
            var receipt = new CityIntentReceipt
            {
                sessionId = "session:test",
                intentId = "intent:0001",
                cityId = "city:1001",
                status = CityIntentStatus.RevisionConflict,
                errorCode = CityModeErrorCode.RevisionConflict,
                resultingWorldTick = 4802,
                resultingStateRevision = 44,
                message = "Refresh snapshot before retry."
            };
            Assert.IsTrue(receipt.TryValidate(out var error), error.ToString());
        }

        [Test]
        public void HostedSession_RejectsDoubleInstanceUntilDisposed()
        {
            var context = ValidContext();
            var gateway = new FakeGateway(context);
            Assert.IsTrue(CityModeSession.TryOpen(
                context, gateway, gateway, out var first, out var error), error.ToString());
            try
            {
                Assert.IsFalse(CityModeSession.TryOpen(
                    context, gateway, gateway, out var second, out error));
                Assert.IsNull(second);
                Assert.AreEqual(CityModeErrorCode.SessionAlreadyActive, error);
            }
            finally
            {
                first.Dispose();
            }

            Assert.IsTrue(CityModeSession.TryOpen(
                context, gateway, gateway, out var reopened, out error), error.ToString());
            reopened.Dispose();
        }

        [Test]
        public void HostedSession_RejectsStaleIntentBeforeCallingHost()
        {
            var context = ValidContext();
            var gateway = new FakeGateway(context);
            Assert.IsTrue(CityModeSession.TryOpen(
                context, gateway, gateway, out var session, out var error), error.ToString());
            try
            {
                var intent = ValidIntent();
                intent.expectedStateRevision--;
                Assert.IsFalse(session.TrySubmitIntent(intent, out var receipt, out error));
                Assert.AreEqual(CityModeErrorCode.RevisionConflict, error);
                Assert.AreEqual(CityIntentStatus.RevisionConflict, receipt.status);
                Assert.AreEqual(0, gateway.submitCount);
            }
            finally
            {
                session.Dispose();
            }
        }

        static CityLaunchContext ValidContext()
        {
            return new CityLaunchContext
            {
                sessionId = "session:test",
                cityId = "city:1001",
                mapCellId = "cell:10:12",
                worldSeed = 140001,
                worldTick = 4800,
                stateRevision = 42,
                timePolicy = CityWorldTimePolicy.PauseWorld,
                worldTimeScalePermille = 0,
                returnViewId = "main-map",
                returnViewStateJson = "{\"selectedCityId\":\"city:1001\"}"
            };
        }

        static CityIntentEnvelope ValidIntent()
        {
            return new CityIntentEnvelope
            {
                sessionId = "session:test",
                intentId = "intent:0001",
                cityId = "city:1001",
                issuedAtWorldTick = 4800,
                expectedStateRevision = 42,
                intentKind = "construction.place",
                payloadJson = "{\"buildingType\":\"granary\",\"xMm\":12000,\"zMm\":8000}"
            };
        }

        sealed class FakeGateway : ICityModeSnapshotSource, ICityModeIntentSink
        {
            readonly CitySnapshotEnvelope snapshot;
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
                return new CityIntentReceipt
                {
                    sessionId = intent.sessionId,
                    intentId = intent.intentId,
                    cityId = intent.cityId,
                    status = CityIntentStatus.Accepted,
                    errorCode = CityModeErrorCode.None,
                    resultingWorldTick = snapshot.worldTick + 1,
                    resultingStateRevision = snapshot.stateRevision + 1
                };
            }
        }
    }
}
