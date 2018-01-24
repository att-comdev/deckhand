import logging
import networkx
import sys
import yaml

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:%(funcName)s [%(lineno)3d] %(message)s'  # noqa

LOG = logging.getLogger(__name__)


if __name__ == '__main__':
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)

    from deckhand.engine import v2
    import deckhand.engine.v2.validation

    with open('example-for-dag.yaml') as f:
        dicts = list(yaml.safe_load_all(f))

    e = v2.Engine([v2.CompleteDocument(d) for d in dicts])
    networkx.write_gexf(e.graph, 'out.gexf')

    if e.has_cycles:
        LOG.error('Document collection has cycles')

    missing_documents = e.find_missing_documents()
    LOG.info('missing_documents: %s', missing_documents)

    try:
        e.render()
    except v2.errors.EngineError as e:
        LOG.exception('Got reject=%s error during rendering', e.reject)
        sys.exit(1)
