using System;

namespace Victoria.CityMode.Integration
{
    /// <summary>
    /// Versioned boundary between a world host (ForgeHistory in production) and
    /// the City Mode presentation. This file intentionally has no Unity dependency.
    /// </summary>
    public static class CityModeProtocol
    {
        public const int Current = 1;
        public const int MinimumSupported = 1;
        public const int SnapshotSchema = 1;
        public const int IntentSchema = 1;

        public static bool IsSupported(int version)
        {
            return version >= MinimumSupported && version <= Current;
        }
    }

    public enum CityWorldTimePolicy
    {
        Unspecified = 0,
        PauseWorld = 1,
        ContinueWorld = 2,
        ScaledWorld = 3
    }

    public enum CityIntentStatus
    {
        Unspecified = 0,
        Accepted = 1,
        Rejected = 2,
        Duplicate = 3,
        RevisionConflict = 4
    }

    public enum CityModeErrorCode
    {
        None = 0,
        InvalidProtocolVersion = 1,
        InvalidSessionId = 2,
        InvalidCityId = 3,
        InvalidMapCellId = 4,
        InvalidWorldTick = 5,
        InvalidStateRevision = 6,
        InvalidTimePolicy = 7,
        InvalidPayload = 8,
        SnapshotUnavailable = 9,
        RevisionConflict = 10,
        DuplicateIntent = 11,
        Cancelled = 12,
        Timeout = 13,
        HostUnavailable = 14,
        InternalError = 15,
        SessionAlreadyActive = 16
    }

    [Serializable]
    public sealed class CityLaunchContext
    {
        public int protocolVersion = CityModeProtocol.Current;
        public string sessionId = string.Empty;
        public string cityId = string.Empty;
        public string mapCellId = string.Empty;
        public int worldSeed;
        public long worldTick;
        public long stateRevision;
        public CityWorldTimePolicy timePolicy = CityWorldTimePolicy.PauseWorld;
        public int worldTimeScalePermille;
        public string returnViewId = string.Empty;
        public string returnViewStateJson = "{}";

        public bool TryValidate(out CityModeErrorCode error)
        {
            return CityModeContractValidation.TryValidate(this, out error);
        }
    }

    [Serializable]
    public sealed class CitySnapshotEnvelope
    {
        public int protocolVersion = CityModeProtocol.Current;
        public int payloadSchemaVersion = CityModeProtocol.SnapshotSchema;
        public string cityId = string.Empty;
        public long worldTick;
        public long stateRevision;
        public bool isFullSnapshot = true;
        public string payloadJson = string.Empty;
        public string payloadSha256 = string.Empty;

        public bool TryValidate(out CityModeErrorCode error)
        {
            return CityModeContractValidation.TryValidate(this, out error);
        }
    }

    [Serializable]
    public sealed class CityIntentEnvelope
    {
        public int protocolVersion = CityModeProtocol.Current;
        public int payloadSchemaVersion = CityModeProtocol.IntentSchema;
        public string sessionId = string.Empty;
        public string intentId = string.Empty;
        public string cityId = string.Empty;
        public long issuedAtWorldTick;
        public long expectedStateRevision;
        public string intentKind = string.Empty;
        public string payloadJson = "{}";

        public bool TryValidate(out CityModeErrorCode error)
        {
            return CityModeContractValidation.TryValidate(this, out error);
        }
    }

    [Serializable]
    public sealed class CityIntentReceipt
    {
        public int protocolVersion = CityModeProtocol.Current;
        public string sessionId = string.Empty;
        public string intentId = string.Empty;
        public string cityId = string.Empty;
        public CityIntentStatus status;
        public CityModeErrorCode errorCode;
        public long resultingWorldTick;
        public long resultingStateRevision;
        public string message = string.Empty;

        public bool TryValidate(out CityModeErrorCode error)
        {
            return CityModeContractValidation.TryValidate(this, out error);
        }
    }

    /// <summary>
    /// Implemented by the authoritative host. City Mode must not tick or persist
    /// a second simulation when this source is present.
    /// </summary>
    public interface ICityModeSnapshotSource
    {
        CitySnapshotEnvelope ReadSnapshot(CityLaunchContext context);
    }

    /// <summary>
    /// Implemented by the authoritative host. Replaying an intentId must be
    /// idempotent and return Duplicate or the original accepted receipt.
    /// </summary>
    public interface ICityModeIntentSink
    {
        CityIntentReceipt SubmitIntent(CityIntentEnvelope intent);
    }

    /// <summary>
    /// Explicit, single-instance lifecycle owned by the host. This object only
    /// coordinates contracts: it never creates a Unity scene, ticks a simulation,
    /// or writes a save file.
    /// </summary>
    public sealed class CityModeSession : IDisposable
    {
        static readonly object Gate = new object();
        static CityModeSession active;

        readonly ICityModeSnapshotSource snapshotSource;
        readonly ICityModeIntentSink intentSink;
        bool disposed;

        CityModeSession(
            CityLaunchContext context,
            ICityModeSnapshotSource snapshotSource,
            ICityModeIntentSink intentSink,
            CitySnapshotEnvelope snapshot)
        {
            Context = context;
            this.snapshotSource = snapshotSource;
            this.intentSink = intentSink;
            CurrentSnapshot = snapshot;
        }

        public CityLaunchContext Context { get; private set; }
        public CitySnapshotEnvelope CurrentSnapshot { get; private set; }
        public bool IsDisposed { get { return disposed; } }

        public static bool TryOpen(
            CityLaunchContext context,
            ICityModeSnapshotSource snapshotSource,
            ICityModeIntentSink intentSink,
            out CityModeSession session,
            out CityModeErrorCode error)
        {
            session = null;
            if (!CityModeContractValidation.TryValidate(context, out error))
                return false;
            if (snapshotSource == null || intentSink == null)
                return FailOpen(CityModeErrorCode.HostUnavailable, out error);

            lock (Gate)
            {
                if (active != null && !active.disposed)
                    return FailOpen(CityModeErrorCode.SessionAlreadyActive, out error);

                CitySnapshotEnvelope snapshot;
                try
                {
                    snapshot = snapshotSource.ReadSnapshot(context);
                }
                catch
                {
                    return FailOpen(CityModeErrorCode.SnapshotUnavailable, out error);
                }
                if (!CityModeContractValidation.TryValidate(snapshot, out error))
                    return false;
                if (!SnapshotMatchesContext(context, snapshot, out error))
                    return false;

                session = new CityModeSession(context, snapshotSource, intentSink, snapshot);
                active = session;
                error = CityModeErrorCode.None;
                return true;
            }
        }

        public bool TryRefreshSnapshot(out CityModeErrorCode error)
        {
            if (disposed)
                return FailOpen(CityModeErrorCode.HostUnavailable, out error);
            CitySnapshotEnvelope next;
            try
            {
                next = snapshotSource.ReadSnapshot(Context);
            }
            catch
            {
                return FailOpen(CityModeErrorCode.SnapshotUnavailable, out error);
            }
            if (!CityModeContractValidation.TryValidate(next, out error))
                return false;
            if (next.cityId != Context.cityId)
                return FailOpen(CityModeErrorCode.InvalidCityId, out error);
            if (next.worldTick < CurrentSnapshot.worldTick)
                return FailOpen(CityModeErrorCode.InvalidWorldTick, out error);
            if (next.stateRevision < CurrentSnapshot.stateRevision)
                return FailOpen(CityModeErrorCode.InvalidStateRevision, out error);
            CurrentSnapshot = next;
            error = CityModeErrorCode.None;
            return true;
        }

        public bool TrySubmitIntent(
            CityIntentEnvelope intent,
            out CityIntentReceipt receipt,
            out CityModeErrorCode error)
        {
            receipt = null;
            if (disposed)
                return FailOpen(CityModeErrorCode.HostUnavailable, out error);
            if (!CityModeContractValidation.TryValidate(intent, out error))
                return false;
            if (intent.sessionId != Context.sessionId)
                return FailOpen(CityModeErrorCode.InvalidSessionId, out error);
            if (intent.cityId != Context.cityId)
                return FailOpen(CityModeErrorCode.InvalidCityId, out error);
            if (intent.expectedStateRevision != CurrentSnapshot.stateRevision)
            {
                receipt = ConflictReceipt(intent, CurrentSnapshot);
                return FailOpen(CityModeErrorCode.RevisionConflict, out error);
            }

            try
            {
                receipt = intentSink.SubmitIntent(intent);
            }
            catch
            {
                return FailOpen(CityModeErrorCode.HostUnavailable, out error);
            }
            if (!CityModeContractValidation.TryValidate(receipt, out error))
                return false;
            if (receipt.sessionId != intent.sessionId || receipt.intentId != intent.intentId ||
                receipt.cityId != intent.cityId)
                return FailOpen(CityModeErrorCode.InvalidPayload, out error);
            if (receipt.resultingWorldTick < CurrentSnapshot.worldTick ||
                receipt.resultingStateRevision < CurrentSnapshot.stateRevision)
                return FailOpen(CityModeErrorCode.InvalidStateRevision, out error);
            error = receipt.errorCode;
            return receipt.status == CityIntentStatus.Accepted ||
                receipt.status == CityIntentStatus.Duplicate;
        }

        public void Dispose()
        {
            lock (Gate)
            {
                if (disposed)
                    return;
                disposed = true;
                if (ReferenceEquals(active, this))
                    active = null;
            }
        }

        static bool SnapshotMatchesContext(
            CityLaunchContext context,
            CitySnapshotEnvelope snapshot,
            out CityModeErrorCode error)
        {
            if (snapshot.cityId != context.cityId)
                return FailOpen(CityModeErrorCode.InvalidCityId, out error);
            if (snapshot.worldTick < context.worldTick)
                return FailOpen(CityModeErrorCode.InvalidWorldTick, out error);
            if (snapshot.stateRevision < context.stateRevision)
                return FailOpen(CityModeErrorCode.InvalidStateRevision, out error);
            if (context.timePolicy == CityWorldTimePolicy.PauseWorld &&
                (snapshot.worldTick != context.worldTick ||
                 snapshot.stateRevision != context.stateRevision))
                return FailOpen(CityModeErrorCode.RevisionConflict, out error);
            error = CityModeErrorCode.None;
            return true;
        }

        static CityIntentReceipt ConflictReceipt(
            CityIntentEnvelope intent,
            CitySnapshotEnvelope snapshot)
        {
            return new CityIntentReceipt
            {
                sessionId = intent.sessionId,
                intentId = intent.intentId,
                cityId = intent.cityId,
                status = CityIntentStatus.RevisionConflict,
                errorCode = CityModeErrorCode.RevisionConflict,
                resultingWorldTick = snapshot.worldTick,
                resultingStateRevision = snapshot.stateRevision,
                message = "Refresh the authoritative snapshot before retrying."
            };
        }

        static bool FailOpen(CityModeErrorCode value, out CityModeErrorCode error)
        {
            error = value;
            return false;
        }
    }

    public static class CityModeContractValidation
    {
        public static bool TryValidate(CityLaunchContext value, out CityModeErrorCode error)
        {
            if (value == null || !CityModeProtocol.IsSupported(value.protocolVersion))
                return Fail(CityModeErrorCode.InvalidProtocolVersion, out error);
            if (IsBlank(value.sessionId))
                return Fail(CityModeErrorCode.InvalidSessionId, out error);
            if (IsBlank(value.cityId))
                return Fail(CityModeErrorCode.InvalidCityId, out error);
            if (IsBlank(value.mapCellId))
                return Fail(CityModeErrorCode.InvalidMapCellId, out error);
            if (value.worldTick < 0)
                return Fail(CityModeErrorCode.InvalidWorldTick, out error);
            if (value.stateRevision < 0)
                return Fail(CityModeErrorCode.InvalidStateRevision, out error);
            if (!IsValidTimePolicy(value.timePolicy, value.worldTimeScalePermille))
                return Fail(CityModeErrorCode.InvalidTimePolicy, out error);
            if (IsBlank(value.returnViewId) || IsBlank(value.returnViewStateJson))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            error = CityModeErrorCode.None;
            return true;
        }

        public static bool TryValidate(CitySnapshotEnvelope value, out CityModeErrorCode error)
        {
            if (value == null || !CityModeProtocol.IsSupported(value.protocolVersion))
                return Fail(CityModeErrorCode.InvalidProtocolVersion, out error);
            if (value.payloadSchemaVersion != CityModeProtocol.SnapshotSchema)
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            if (IsBlank(value.cityId))
                return Fail(CityModeErrorCode.InvalidCityId, out error);
            if (value.worldTick < 0)
                return Fail(CityModeErrorCode.InvalidWorldTick, out error);
            if (value.stateRevision < 0)
                return Fail(CityModeErrorCode.InvalidStateRevision, out error);
            if (!value.isFullSnapshot || IsBlank(value.payloadJson) || !IsSha256(value.payloadSha256))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            error = CityModeErrorCode.None;
            return true;
        }

        public static bool TryValidate(CityIntentEnvelope value, out CityModeErrorCode error)
        {
            if (value == null || !CityModeProtocol.IsSupported(value.protocolVersion))
                return Fail(CityModeErrorCode.InvalidProtocolVersion, out error);
            if (value.payloadSchemaVersion != CityModeProtocol.IntentSchema)
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            if (IsBlank(value.sessionId))
                return Fail(CityModeErrorCode.InvalidSessionId, out error);
            if (IsBlank(value.intentId))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            if (IsBlank(value.cityId))
                return Fail(CityModeErrorCode.InvalidCityId, out error);
            if (value.issuedAtWorldTick < 0)
                return Fail(CityModeErrorCode.InvalidWorldTick, out error);
            if (value.expectedStateRevision < 0)
                return Fail(CityModeErrorCode.InvalidStateRevision, out error);
            if (IsBlank(value.intentKind) || IsBlank(value.payloadJson))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            error = CityModeErrorCode.None;
            return true;
        }

        public static bool TryValidate(CityIntentReceipt value, out CityModeErrorCode error)
        {
            if (value == null || !CityModeProtocol.IsSupported(value.protocolVersion))
                return Fail(CityModeErrorCode.InvalidProtocolVersion, out error);
            if (IsBlank(value.sessionId))
                return Fail(CityModeErrorCode.InvalidSessionId, out error);
            if (IsBlank(value.intentId))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            if (IsBlank(value.cityId))
                return Fail(CityModeErrorCode.InvalidCityId, out error);
            if (value.resultingWorldTick < 0)
                return Fail(CityModeErrorCode.InvalidWorldTick, out error);
            if (value.resultingStateRevision < 0)
                return Fail(CityModeErrorCode.InvalidStateRevision, out error);
            if (!IsValidReceipt(value.status, value.errorCode))
                return Fail(CityModeErrorCode.InvalidPayload, out error);
            error = CityModeErrorCode.None;
            return true;
        }

        static bool IsValidTimePolicy(CityWorldTimePolicy policy, int scalePermille)
        {
            switch (policy)
            {
                case CityWorldTimePolicy.PauseWorld:
                    return scalePermille == 0;
                case CityWorldTimePolicy.ContinueWorld:
                    return scalePermille == 1000;
                case CityWorldTimePolicy.ScaledWorld:
                    return scalePermille >= 1 && scalePermille <= 4000;
                default:
                    return false;
            }
        }

        static bool IsValidReceipt(CityIntentStatus status, CityModeErrorCode error)
        {
            if (status == CityIntentStatus.Accepted)
                return error == CityModeErrorCode.None;
            if (status == CityIntentStatus.Duplicate)
                return error == CityModeErrorCode.None || error == CityModeErrorCode.DuplicateIntent;
            if (status == CityIntentStatus.RevisionConflict)
                return error == CityModeErrorCode.RevisionConflict;
            return status == CityIntentStatus.Rejected && error != CityModeErrorCode.None;
        }

        static bool IsSha256(string value)
        {
            if (value == null || value.Length != 64)
                return false;
            for (var i = 0; i < value.Length; i++)
            {
                var c = value[i];
                if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
                    return false;
            }
            return true;
        }

        static bool IsBlank(string value)
        {
            return string.IsNullOrWhiteSpace(value);
        }

        static bool Fail(CityModeErrorCode value, out CityModeErrorCode error)
        {
            error = value;
            return false;
        }
    }
}
