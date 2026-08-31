from app.extensions import db

class Visitor(db.Model):
    __tablename__ = 'visitors'

    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id   = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20),  nullable=True)
    expected_date = db.Column(db.Date,        nullable=True)
    expected_time = db.Column(db.Time,        nullable=True)
    pass_code     = db.Column(db.String(20),  nullable=False, unique=True)
    id_verified   = db.Column(db.Boolean,     default=False)
    status        = db.Column(db.Enum('awaiting_approval','pre_registered', 'checked_in', 'checked_out', 'rejected', name='visitor_status'), default='pre_registered')
    check_in_time = db.Column(db.DateTime,    nullable=True)
    check_out_time= db.Column(db.DateTime,    nullable=True)
    created_at    = db.Column(db.DateTime,    default=__import__('datetime').datetime.utcnow)

    vehicle_number = db.Column(db.String(20), nullable=True)
    reason         = db.Column(db.Text, nullable=True)


    is_expired     = db.Column(db.Boolean, default=False)
    # ADDED — distinguishes how the pass was created. Separate from
    # `status`, which tracks workflow state, not origin.
    visit_type = db.Column(
        db.Enum('pre_registered', 'walk_in', name='visitor_visit_type'),
        default='pre_registered',
        nullable=False,
    )
 
    # ADDED — real expiry timestamp. Replaces the old static `is_expired`
    # boolean as the source of truth; expiry is now computed dynamically
    # from this instead of needing a background job to flip a flag.
    expires_at = db.Column(db.DateTime, nullable=True)
 
    # ADDED — revoke is tracked separately from `status` so a
    # resident-cancelled pass never looks identical to a security-rejected
    # or a timed-out one.
    revoked    = db.Column(db.Boolean, default=False, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    # ADDED — whether the pass can be used for repeat entries (e.g. a
    # maid/driver) rather than a single visit. Independent of
    # validity_mode below — either use-type can pick any validity mode.
    is_multi_use = db.Column(db.Boolean, default=True, nullable=False)

    # ADDED — optional end date for an open-ended (no_date) multi-use
    # pass. Only meaningful when validity_mode == 'no_date'; for
    # exact_date/until_date passes, expected_date drives expiry instead.
    valid_until = db.Column(db.Date, nullable=True)

    # ADDED — the date window a pre-registered pass is usable in:
    #   exact_date — usable only on expected_date, not before, not after
    #   until_date — usable any time up through the end of expected_date
    #   no_date    — no expected_date required; open-ended (or bound by
    #                the optional valid_until above)
    validity_mode = db.Column(
        db.Enum('exact_date', 'until_date', 'no_date', name='visitor_validity_mode'),
        default='no_date',
        nullable=False,
    )
    def __repr__(self):
        return f'<Visitor {self.name} ({self.status})>'