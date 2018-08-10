####################################
# My Own changes : loop added for continuous training
####################################

from __future__ import print_function

import os
from utils import *
from random import shuffle
from os.path import join
from time import time
import torch
import torch.nn as nn
from torch.autograd import Variable
import torch.optim as optim
from PIL import Image
import matplotlib.pyplot as plt
import torchvision.transforms as transforms
import torchvision.models as models
import copy
import warnings
warnings.filterwarnings('ignore')

path_to_cropped_imgs = '/ssd480/grisha/plates_generation/generated_400000_cropped_VJ'
path_to_save = '/ssd480/grisha/style_transfer/result'
num_style_imgs = 30

loader = transforms.Compose([
    transforms.Scale(imsize),  # scale imported image
    transforms.ToTensor()])  # transform it into a torch tensor

unloader = transforms.ToPILImage()  # reconvert into PIL image

use_cuda = torch.cuda.is_available()
dtype = torch.cuda.FloatTensor if use_cuda else torch.FloatTensor

cnn = models.vgg19(pretrained=True).features
# move it to the GPU if possible:
if use_cuda:
    cnn = cnn.cuda()


def image_loader(image_name):
    image = cv2.imread(image_name)
    image = Image.fromarray(image)

    #     image = Image.open(image_name)
    image = image.resize((imsize, imsize), Image.ANTIALIAS)
    image = Variable(loader(image))
    # fake batch dimension required to fit network's input dimensions
    image = image.unsqueeze(0)
    return image


def image_loader_generated():
    # we don't load but generate an image
    image = get_random_plate()
    # we have to save and write image, otherwise we can't get third dimension equal to 3
    cv2.imwrite('temp.jpg', image)
    image = cv2.imread('temp.jpg')
    image = Image.fromarray(image)

    #     image = Image.open(image_name)
    image = image.resize((imsize, imsize), Image.ANTIALIAS)
    image = Variable(loader(image))
    # fake batch dimension required to fit network's input dimensions
    image = image.unsqueeze(0)
    return image


def imshow(tensor, title=None):
    image = tensor.clone().cpu()  # we clone the tensor to not do changes on it
    image = image.view(3, imsize, imsize)  # remove the fake batch dimension
    image = unloader(image)
    plt.imshow(image)
    if title is not None:
        plt.title(title)
    plt.pause(0.001)  # pause a bit so that plots are updated


def imsave(tensor, title):
    image = tensor.clone().cpu()  # we clone the tensor to not do changes on it
    image = image.view(3, imsize, imsize)  # remove the fake batch dimension
    image = unloader(image)
    image.save(title)


class ContentLoss(nn.Module):

    def __init__(self, target, weight):
        super(ContentLoss, self).__init__()
        # we 'detach' the target content from the tree used
        self.target = target.detach() * weight
        # to dynamically compute the gradient: this is a stated value,
        # not a variable. Otherwise the forward method of the criterion
        # will throw an error.
        self.weight = weight
        self.criterion = nn.MSELoss()

    def forward(self, input):
        self.loss = self.criterion(input * self.weight, self.target)
        self.output = input
        return self.output

    def backward(self, retain_graph=True):
        self.loss.backward(retain_graph=retain_graph)
        return self.loss


class GramMatrix(nn.Module):

    def forward(self, input):
        N, C, H, W = input.size()  # N=batch size(=1)
        # C=number of feature maps
        # (H,W)=dimensions of a f. map (M=H*W)

        features = input.view(N * C, H * W)  # resise F_XL into \hat F_XL

        G = torch.mm(features, features.t())  # compute the gram product

        # we 'normalize' the values of the gram matrix
        # by dividing by the number of element in each feature maps.
        return G.div(N * C * H * W)


class StyleLoss(nn.Module):

    def __init__(self, target, weight):
        super(StyleLoss, self).__init__()
        self.target = target.detach() * weight
        self.weight = weight
        self.gram = GramMatrix()
        self.criterion = nn.MSELoss()

    def forward(self, input):
        self.output = input.clone()
        self.G = self.gram(input)
        self.G.mul_(self.weight)
        self.loss = self.criterion(self.G, self.target)
        return self.output

    def backward(self, retain_graph=True):
        self.loss.backward(retain_graph=retain_graph)
        return self.loss


# desired depth layers to compute style/content losses :
content_layers_default = ['conv_4']
style_layers_default = ['conv_1', 'conv_2', 'conv_3', 'conv_4', 'conv_5']
def get_style_model_and_losses(cnn, style_img, content_img, style_weight=1000, content_weight=1,
                               content_layers=content_layers_default,
                               style_layers=style_layers_default):
    cnn = copy.deepcopy(cnn)

    # just in order to have an iterable access to or list of content/syle
    # losses
    content_losses = []
    style_losses = []

    model = nn.Sequential()  # the new Sequential module network
    gram = GramMatrix()  # we need a gram module in order to compute style targets

    # move these modules to the GPU if possible:
    if use_cuda:
        model = model.cuda()
        gram = gram.cuda()

    i = 1
    for layer in list(cnn):
        if isinstance(layer, nn.Conv2d):
            name = "conv_" + str(i)
            model.add_module(name, layer)

            if name in content_layers:
                # add content loss:
                target = model(content_img).clone()
                content_loss = ContentLoss(target, content_weight)
                model.add_module("content_loss_" + str(i), content_loss)
                content_losses.append(content_loss)

            if name in style_layers:
                # add style loss:
                target_feature = model(style_img).clone()
                target_feature_gram = gram(target_feature)
                style_loss = StyleLoss(target_feature_gram, style_weight)
                model.add_module("style_loss_" + str(i), style_loss)
                style_losses.append(style_loss)

        if isinstance(layer, nn.ReLU):
            name = "relu_" + str(i)
            model.add_module(name, layer)

            if name in content_layers:
                # add content loss:
                target = model(content_img).clone()
                content_loss = ContentLoss(target, content_weight)
                model.add_module("content_loss_" + str(i), content_loss)
                content_losses.append(content_loss)

            if name in style_layers:
                # add style loss:
                target_feature = model(style_img).clone()
                target_feature_gram = gram(target_feature)
                style_loss = StyleLoss(target_feature_gram, style_weight)
                model.add_module("style_loss_" + str(i), style_loss)
                style_losses.append(style_loss)

            i += 1

        if isinstance(layer, nn.MaxPool2d):
            name = "pool_" + str(i)
            model.add_module(name, layer)  # ***

    return model, style_losses, content_losses


def get_input_param_optimizer(input_img):
    # this line to show that input is a parameter that requires a gradient
    input_param = nn.Parameter(input_img.data)
    optimizer = optim.LBFGS([input_param])
    return input_param, optimizer


def run_style_transfer(cnn, content_img, style_img, input_img, num_steps=300,
                       style_weight=1000, content_weight=1):
    """Run the style transfer."""
    # получим нашу модель и ссылки на лосс слои
    model, style_losses, content_losses = get_style_model_and_losses(cnn,
                                                                     style_img, content_img, style_weight,
                                                                     content_weight)
    input_param, optimizer = get_input_param_optimizer(input_img)

    run = [0]
    while run[0] <= num_steps:

        def closure():
            # correct the values of updated input image
            input_param.data.clamp_(0, 1)

            # очистим старые значения градиентов
            optimizer.zero_grad()
            # прогоним изображение. Здесь мы посчитаем все карты признаков, а также значения фу
            model(input_param)
            style_score = 0
            content_score = 0

            # считаем градиенты для каждого лосс слоя и достаем значение ошибки из сети
            for sl in style_losses:
                style_score += sl.backward()
            for cl in content_losses:
                content_score += cl.backward()

            run[0] += 1

            # каждые 50 итераций будем проверять прогресс
            # if run[0] % 50 == 0:
            #     print("run {}:".format(run))
            #     print('Style Loss : {:4f} Content Loss: {:4f}'.format(
            #         style_score.data[0], content_score.data[0]))
            #     print()

            return style_score + content_score

        # сделаем оптимизационный шаг
        optimizer.step(closure)

    # a last correction...
    input_param.data.clamp_(0, 1)

    return input_param.data


style_imgs = os.listdir(path_to_cropped_imgs)
shuffle(style_imgs)
style_imgs = [x for x in style_imgs if '_temp' not in x]
style_imgs = style_imgs[:num_style_imgs]

t = 0
print('Building the style transfer model..')
print('Optimizing {} images'.format(len(style_imgs)))
for i, item in enumerate(style_imgs):
    style_img = image_loader(join(path_to_cropped_imgs, item)).type(dtype)
    content_img = image_loader_generated().type(dtype)
    assert style_img.size() == content_img.size(), "style and content images are not of the same size"
    input_img = content_img.clone()

    t0 = time()
    output = run_style_transfer(cnn, content_img, style_img, input_img, style_weight=500, num_steps=150)
    t += time() - t0
    imsave(output, join(path_to_save, item))

    if i % 5 == 0:
        print('{} images are ready'.format(i))

print('-'*30)
print('Average time per sample - {:.2f} sec'.format(t/len(style_imgs)))
print('-'*30)

