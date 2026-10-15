<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card border-0 shadow-sm">
            <div class="card-header bg-white fw-bold">New Company</div>
            <div class="card-body">
                <form method="POST" action="index.php?route=companies/store">
                    <?= \Core\Csrf::field() ?>
                    <div class="mb-3">
                        <label class="form-label">Company Name *</label>
                        <input type="text" name="name" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Industry</label>
                        <input type="text" name="industry" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Phone</label>
                        <input type="text" name="phone" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Email</label>
                        <input type="email" name="email" class="form-control">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Website</label>
                        <input type="url" name="website" class="form-control" placeholder="https://example.com">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Address</label>
                        <textarea name="address" class="form-control" rows="2"></textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Save</button>
                    <a href="index.php?route=companies" class="btn btn-light">Cancel</a>
                </form>
            </div>
        </div>
    </div>
</div>