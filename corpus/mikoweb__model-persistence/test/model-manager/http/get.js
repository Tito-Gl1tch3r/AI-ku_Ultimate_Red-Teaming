describe('model-manager.HTTPModelManager', () => {
    const factory = modelPersist.httpFactory;

    beforeEach(() => {
        moxios.install()
    });

    afterEach(() => {
        moxios.uninstall()
    });

    it('get model', () => {
        class Locator extends modelPersist.HTTPLocatorAbstract {
            get basePath() {
                return '/article';
            }
        }

        const locator = new Locator();
        const manager = factory.createManager(locator);
        const Model = new modelPersist.Model({
            id: Number,
            title: String,
            content: String
        });

        moxios.wait(() => {
            const request = moxios.requests.mostRecent();

            expect('/article/100').to.equal(request.url);
            expect('get').to.equal(request.config.method);

            request.respondWith({
                status: 200,
                response: {
                    id: 100,
                    title: 'Lorem Ipsum',
                    content: '<p>Lorem Ipsum</p>'
                }
            });
        });

        return manager.get(100, Model).then((model) => {
            expect(100).to.equal(model.id);
            expect('Lorem Ipsum').to.equal(model.title);
            expect('<p>Lorem Ipsum</p>').to.equal(model.content);
        });
    });
});
