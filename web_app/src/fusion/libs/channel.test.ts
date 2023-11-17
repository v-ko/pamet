import { addChannel, HandlerFunction, Channel, clearChannels } from './channel'; // Assuming this is the file name

describe('Channel', () => {
    let channel: Channel;
    let mockHandler: jest.Mock<HandlerFunction>;
    let mockHandler2: jest.Mock<HandlerFunction>;
    let mockFilter: jest.Mock;

    beforeEach(() => {
        // Setup a new channel for each test to avoid state leakage
        channel = addChannel('test');
        mockHandler = jest.fn();
        mockHandler2 = jest.fn();
        mockFilter = jest.fn().mockReturnValue(true); // default to always passing filter
        // mockHandler.mockClear();
        clearChannels(); // Clear all subscriptions between tests
    });

    test('should call a subscribed handler with the correct message', done => {
        channel.subscribe(mockHandler);
        channel.push('test message');

        // Since `callDelayed` uses `queueMicrotask`, we need to wait for the microtask queue to be flushed
        queueMicrotask(() => {
            // The assertion is placed inside a `queueMicrotask` call to ensure it runs after the handler has been called
            expect(mockHandler).toHaveBeenCalledWith('test message');
            done();
        });
    });

    test('should not call the handler if the filterKey rejects the message', done => {
        // Define a filter that rejects every message
        channel.filterKey = () => false;

        // Subscribe the mock handler to the test channel
        channel.subscribe(mockHandler);

        // Push a message that should be filtered out
        channel.push('test message');

        // Check after microtasks have been processed that the handler has not been called
        queueMicrotask(() => {
          expect(mockHandler).not.toHaveBeenCalled();
          done();
        });
      });

//   test('handles indexed subscription and dispatching', done => {
//     channel.subscribe(mockHandler, 'index1');
//     channel.subscribe(mockHandler2, 'index2');

//     channel.push({ data: 'message for index1', index: 'index1', filter: true });
//     // expect(mockHandler).toHaveBeenCalledWith({ data: 'message for index1', index: 'index1', filter: true });
//     // expect(mockHandler2).not.toHaveBeenCalled();
//     queueMicrotask(() => {
//         expect(mockHandler).toHaveBeenCalledWith({ data: 'message for index1', index: 'index1', filter: true });
//         expect(mockHandler2).not.toHaveBeenCalled();
//         done();
//     });


//     channel.push({ data: 'message for index2', index: 'index2', filter: true });
//     // expect(mockHandler2).toHaveBeenCalledWith({ data: 'message for index2', index: 'index2', filter: true });
//     queueMicrotask(() => {
//         expect(mockHandler2).toHaveBeenCalledWith({ data: 'message for index2', index: 'index2', filter: true });
//         done();
//     });
//   });

//   test('unsubscribes handlers correctly', () => {
//     const subscription = channel.subscribe(mockHandler);
//     channel.push({ data: 'before unsubscribe', index: null, filter: true });
//     expect(mockHandler).toHaveBeenCalledTimes(1);

//     subscription.unsubscribe();
//     channel.push({ data: 'after unsubscribe', index: null, filter: true });
//     expect(mockHandler).toHaveBeenCalledTimes(1); // Should still be 1 if unsubscribed correctly
//   });

});
