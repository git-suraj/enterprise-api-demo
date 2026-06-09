# Metering and Billing Walkthrough

Metering and Billing setup. <br>
`Meter request -> create feature -> create plans and add feature and add rate card -> publish plan -> create customers -> subscribe to plan`

## Step 1

![Step 1](IMG/1.png)

Create meter:
- Group by - elements which will help you filter requests later.

## Step 2

![Step 2](IMG/2.png)

Create feature:
- When creating the feature make sure you filter based on relevant criteria - in this case it is by control plane id and route name. You could probably also have it by status code so that only successful requests are billed

## Step 3

![Step 3](IMG/3.png)

Create the plans:
- Two plans in this case - standard and premium

## Step 4

![Step 4](IMG/4.png)

Add rate card:
- In the plan add the rate card
- Select usage based pricing
- Apply price per unit
- Entitlement - None
- Publish the plan

## Step 5

![Step 5](IMG/5.png)

Add rate card:
- Same as above for the other plans as well

## Step 6

![Step 6](IMG/6.png)

Create customers:
- Note the id from the consumers section of the gatweway and use that to add it here


![Step 7](IMG/7.png)

## Step 7

![Step 7](IMG/8.png)

Susbcription:
- Customer subscribes to the appropriate plan
